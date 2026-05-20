"""
db.py — Consulta la lista de DVRs desde api.batidospitaya.com/api/hikvision/
Reutiliza el mismo token y base_url que el proyecto principal.
No hay conexión directa a MySQL; todo va vía API REST.
"""

import requests
from . import config
from .logger import get_logger

log = get_logger('db')

_HEADERS = {
    'X-WSP-Token': config.API_TOKEN,
    'Content-Type': 'application/json',
}


def get_dvrs_activos() -> list[dict]:
    """
    Obtiene todos los DVRs con tunel_activo=1 desde la API.
    Retorna lista de dicts con las claves:
      cod_sucursal, nombre_sucursal, portal_ip_local,
      portal_usuario, portal_clave, puerto_http_vps
    Lanza RuntimeError si la consulta falla (aborta el script).
    """
    url = f"{config.API_BASE_URL}/dvr_sucursales.php"
    try:
        r = requests.get(
            url,
            headers=_HEADERS,
            params={'tunel_activo': 1},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Error consultando DVRs en API: {exc}") from exc

    if not data.get('success'):
        raise RuntimeError(f"API respondió con error: {data}")

    dvrs = data.get('dvrs', [])
    log.info(f"DVRs activos obtenidos desde API: {len(dvrs)}")
    return dvrs


def get_dvr_por_codigo(cod_sucursal: int) -> dict | None:
    """
    Obtiene un DVR específico por cod_sucursal.
    Retorna el dict del DVR o None si no existe.
    """
    url = f"{config.API_BASE_URL}/dvr_sucursales.php"
    try:
        r = requests.get(
            url,
            headers=_HEADERS,
            params={'cod_sucursal': cod_sucursal},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Error consultando DVR {cod_sucursal}: {exc}") from exc

    dvrs = data.get('dvrs', [])
    return dvrs[0] if dvrs else None
