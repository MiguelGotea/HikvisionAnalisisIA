"""
hikvision.py — Cliente ISAPI de Hikvision.
Maneja autenticación HTTP Digest, construcción de XML y parseo de respuestas.

Convención de zona horaria Hikvision:
  UTC-6 (Nicaragua / America/Managua) → CST+6:00:00  (sentido invertido)
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

import requests
from requests.auth import HTTPDigestAuth

from . import config
from .logger import get_logger

log = get_logger('hikvision')

# Namespace XML que Hikvision requiere en todos los PUT
_NS = 'http://www.hikvision.com/ver20/XMLSchema'

# ── Payloads XML ──────────────────────────────────────────────

_XML_TIME = """\
<?xml version="1.0" encoding="UTF-8"?>
<Time version="2.0" xmlns="{ns}">
  <timeMode>NTP</timeMode>
  <timeZone>{tz}</timeZone>
</Time>"""

_XML_NTP_SERVER = """\
<?xml version="1.0" encoding="UTF-8"?>
<NTPServer version="2.0" xmlns="{ns}">
  <id>1</id>
  <addressingFormatType>hostname</addressingFormatType>
  <hostName>{host}</hostName>
  <portNo>{port}</portNo>
  <synchronizeInterval>{interval}</synchronizeInterval>
</NTPServer>"""


# ── Estructuras de resultado ──────────────────────────────────

@dataclass
class TimeInfo:
    """Información de tiempo leída del DVR."""
    time_mode: str = ''
    time_zone: str = ''
    raw_xml: str = ''


@dataclass
class NtpServerInfo:
    """Información del servidor NTP leída del DVR."""
    host_name: str = ''
    port: int = 0
    interval: int = 0
    raw_xml: str = ''


# ── Helpers internos ──────────────────────────────────────────

def _base_url(dvr: dict) -> str:
    """
    Construye la URL base HTTP del DVR.
    Si puerto_http_vps está definido (>0) usa el túnel SSH inverso local del VPS:
      El túnel mapea  localhost:{puerto_http_vps}  →  DVR_IP:80
    Si no, accede directamente a la IP local (VPS tiene ruta vía túnel WireGuard/VPN).
    """
    puerto_http = dvr.get('puerto_http_vps') or 0
    if int(puerto_http) > 0:
        # El túnel SSH inverso corre en el VPS: localhost:puerto → DVR remoto
        return f"http://127.0.0.1:{puerto_http}"
    # Sin túnel HTTP: acceso directo a IP privada (ruta disponible vía bridge)
    ip = dvr['portal_ip_local']
    return f"http://{ip}:80"


def _auth(dvr: dict) -> HTTPDigestAuth:
    return HTTPDigestAuth(dvr['portal_usuario'], dvr['portal_clave'])


def _tag(element: ET.Element, local: str) -> Optional[str]:
    """Busca un tag con o sin namespace y retorna su texto."""
    # Con namespace
    found = element.find(f'{{{_NS}}}{local}')
    if found is None:
        # Sin namespace (algunos firmwares viejos no lo incluyen)
        found = element.find(local)
    return found.text.strip() if found is not None and found.text else None


# ── API pública ───────────────────────────────────────────────

def get_time(dvr: dict) -> TimeInfo:
    """
    GET /ISAPI/System/time
    Retorna TimeInfo con timeMode y timeZone actuales.
    Lanza requests.RequestException si hay error de red/auth.
    """
    url = f"{_base_url(dvr)}/ISAPI/System/time"
    label = _label(dvr)
    log.info(f"[{label}] {dvr['portal_ip_local']} — GET /ISAPI/System/time")

    r = requests.get(url, auth=_auth(dvr), timeout=config.TIMEOUT_SEGUNDOS)
    log.info(f"[{label}] {dvr['portal_ip_local']} — GET /ISAPI/System/time → {r.status_code}")
    r.raise_for_status()

    root = ET.fromstring(r.text)
    return TimeInfo(
        time_mode=_tag(root, 'timeMode') or '',
        time_zone=_tag(root, 'timeZone') or '',
        raw_xml=r.text,
    )


def set_time_ntp(dvr: dict) -> int:
    """
    PUT /ISAPI/System/time — Activa modo NTP y configura zona horaria.
    Retorna el HTTP status code.
    """
    url = f"{_base_url(dvr)}/ISAPI/System/time"
    label = _label(dvr)
    body = _XML_TIME.format(ns=_NS, tz=config.HIK_TIMEZONE)

    log.info(f"[{label}] {dvr['portal_ip_local']} — PUT /ISAPI/System/time (timeMode=NTP, tz={config.HIK_TIMEZONE})")
    r = requests.put(
        url,
        auth=_auth(dvr),
        data=body.encode('utf-8'),
        headers={'Content-Type': 'application/xml'},
        timeout=config.TIMEOUT_SEGUNDOS,
    )
    log.info(f"[{label}] {dvr['portal_ip_local']} — PUT /ISAPI/System/time → {r.status_code}")
    r.raise_for_status()
    return r.status_code


def set_ntp_server(dvr: dict) -> int:
    """
    PUT /ISAPI/System/time/NtpServers/1 — Configura servidor NTP.
    Retorna el HTTP status code.
    """
    url = f"{_base_url(dvr)}/ISAPI/System/time/NtpServers/1"
    label = _label(dvr)
    body = _XML_NTP_SERVER.format(
        ns=_NS,
        host=config.NTP_SERVER,
        port=config.NTP_PORT,
        interval=config.NTP_SYNC_INTERVAL,
    )

    log.info(f"[{label}] {dvr['portal_ip_local']} — PUT /ISAPI/System/time/NtpServers/1 (host={config.NTP_SERVER})")
    r = requests.put(
        url,
        auth=_auth(dvr),
        data=body.encode('utf-8'),
        headers={'Content-Type': 'application/xml'},
        timeout=config.TIMEOUT_SEGUNDOS,
    )
    log.info(f"[{label}] {dvr['portal_ip_local']} — PUT /ISAPI/System/time/NtpServers/1 → {r.status_code}")
    r.raise_for_status()
    return r.status_code


def get_ntp_server(dvr: dict) -> NtpServerInfo:
    """
    GET /ISAPI/System/time/NtpServers/1 — Verifica configuración NTP aplicada.
    """
    url = f"{_base_url(dvr)}/ISAPI/System/time/NtpServers/1"
    label = _label(dvr)
    log.info(f"[{label}] {dvr['portal_ip_local']} — GET /ISAPI/System/time/NtpServers/1")

    r = requests.get(url, auth=_auth(dvr), timeout=config.TIMEOUT_SEGUNDOS)
    log.info(f"[{label}] {dvr['portal_ip_local']} — GET /ISAPI/System/time/NtpServers/1 → {r.status_code}")
    r.raise_for_status()

    root = ET.fromstring(r.text)
    return NtpServerInfo(
        host_name=_tag(root, 'hostName') or '',
        port=int(_tag(root, 'portNo') or 0),
        interval=int(_tag(root, 'synchronizeInterval') or 0),
        raw_xml=r.text,
    )


def is_already_ok(time_info: TimeInfo, ntp_info: NtpServerInfo) -> bool:
    """
    Retorna True si el DVR ya tiene NTP activado con time.google.com
    y la zona horaria correcta — sin necesidad de cambio.
    """
    return (
        time_info.time_mode.upper() == 'NTP'
        and time_info.time_zone == config.HIK_TIMEZONE
        and ntp_info.host_name == config.NTP_SERVER
    )


def _label(dvr: dict) -> str:
    """Etiqueta legible para logs: nombre o cod_sucursal."""
    return dvr.get('nombre_sucursal') or str(dvr.get('cod_sucursal', '?'))
