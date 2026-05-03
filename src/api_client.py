"""
api_client.py — Cliente HTTP para api.batidospitaya.com/api/hikvision/
Todas las comunicaciones con Hostinger pasan por aquí.
"""

import requests
from . import config
from .logger import get_logger

log = get_logger('api_client')

HEADERS = {
    'X-WSP-Token': config.API_TOKEN,
    'Content-Type': 'application/json',
}

TIMEOUT = 30  # segundos


def _get(endpoint: str, params: dict = None) -> dict:
    url = f"{config.API_BASE_URL}/{endpoint}"
    r = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _post(endpoint: str, body: dict) -> dict:
    url = f"{config.API_BASE_URL}/{endpoint}"
    r = requests.post(url, headers=HEADERS, json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# ── Endpoints ────────────────────────────────────────────────

def get_next_items(limit: int = 1) -> list:
    """Obtiene los próximos N items pendientes de la cola (atómicamente marcados como 'procesando')."""
    try:
        resp = _get('pedidos_cola.php', params={'limit': limit})
        return resp.get('items', [])
    except Exception as e:
        log.error(f"Error consultando cola: {e}")
        return []


def get_gemini_key() -> dict:
    """Obtiene una API key activa de Gemini con rotación automática."""
    resp = _get('gemini_key.php')
    if not resp.get('success'):
        raise RuntimeError(f"No se pudo obtener key Gemini: {resp}")
    return resp  # {key_id, api_key, modelo}


def mark_failed(id_cola: int, error_msg: str):
    """Marca un item de la cola como fallido con el mensaje de error."""
    try:
        _post('marcar_estado.php', {
            'id_cola': id_cola,
            'estado': 'fallido',
            'error': error_msg[:2000],  # Truncar para evitar payloads enormes
        })
    except Exception as e:
        log.error(f"Error marcando fallido id={id_cola}: {e}")


def save_result(id_cola: int, resultado: dict):
    """Guarda el resultado del análisis IA y marca el item como completado."""
    body = {'id_cola': id_cola, **resultado}
    resp = _post('registrar_resultado.php', body)
    if not resp.get('success'):
        raise RuntimeError(f"Error guardando resultado: {resp}")
    return resp
