"""
notifier.py — Envío de webhook HTTP con el resumen consolidado.
Si NTP_WEBHOOK_URL está vacío, simplemente no envía nada (no es error).
"""

import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict

import requests

from . import config
from .logger import get_logger

log = get_logger('notifier')

# Zona horaria Nicaragua (UTC-6)
_TZ_NIC = timezone(timedelta(hours=-6))


def _timestamp_nic() -> str:
    """Timestamp ISO-8601 en hora Nicaragua."""
    return datetime.now(_TZ_NIC).isoformat(timespec='seconds')


def send_webhook(resultados: List[Dict]) -> bool:
    """
    Envía el resumen de la ejecución al webhook configurado.
    resultados: lista de dicts con keys:
      cod_sucursal, nombre_sucursal, ip, resultado, error (opcional)

    Retorna True si se envió OK (o si no hay webhook configurado).
    Retorna False si falló el envío.
    """
    if not config.WEBHOOK_URL:
        log.info("WEBHOOK_URL no configurada — se omite notificación.")
        return True

    # ── Calcular resumen ──────────────────────────────────────
    conteo = {
        'SUCCESS':    0,
        'ALREADY_OK': 0,
        'UNREACHABLE': 0,
        'AUTH_ERROR': 0,
        'PARTIAL':    0,
        'FAILED':     0,
    }
    for r in resultados:
        estado = r.get('resultado', 'FAILED')
        conteo[estado] = conteo.get(estado, 0) + 1

    payload = {
        'evento': 'ntp_setup_completado',
        'timestamp': _timestamp_nic(),
        'resumen': {
            'total':       len(resultados),
            'success':     conteo['SUCCESS'],
            'already_ok':  conteo['ALREADY_OK'],
            'unreachable': conteo['UNREACHABLE'],
            'auth_error':  conteo['AUTH_ERROR'],
            'partial':     conteo['PARTIAL'],
            'failed':      conteo['FAILED'],
        },
        'detalle': [
            {
                'codigo_local':    r.get('cod_sucursal'),
                'nombre_sucursal': r.get('nombre_sucursal'),
                'ip':              r.get('ip'),
                'resultado':       r.get('resultado'),
                **(({'error': r['error']} if r.get('error') else {})),
            }
            for r in resultados
        ],
    }

    headers = {'Content-Type': 'application/json'}
    if config.WEBHOOK_TOKEN:
        headers['Authorization'] = f"Bearer {config.WEBHOOK_TOKEN}"

    try:
        resp = requests.post(
            config.WEBHOOK_URL,
            data=json.dumps(payload, ensure_ascii=False),
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        log.info(f"Webhook enviado OK → {config.WEBHOOK_URL} [{resp.status_code}]")
        return True
    except requests.RequestException as exc:
        log.error(f"Error enviando webhook: {exc}")
        return False
