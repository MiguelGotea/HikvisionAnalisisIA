"""
config.py — Configuración centralizada desde variables de entorno.
Todos los módulos importan desde aquí. Lee el .env de la raíz del proyecto
principal (HikvisionAnalisisIA/.env) y también acepta sobreescrituras en
dvr_ntp_setup/.env.local si existe.
"""

import os
from dotenv import load_dotenv

# Primero carga el .env raíz del proyecto principal
_root_env = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(_root_env)

# Luego carga override local (dvr_ntp_setup/.env.local) si existe
_local_env = os.path.join(os.path.dirname(__file__), '.env.local')
load_dotenv(_local_env, override=True)


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Variable de entorno requerida no definida: {key}")
    return val


# ── API (misma que usa el proyecto principal) ─────────────────
API_TOKEN    = _require('HIK_API_TOKEN')
API_BASE_URL = os.getenv('HIK_API_BASE_URL', 'https://api.batidospitaya.com/api/hikvision').rstrip('/')

# ── NTP Setup ─────────────────────────────────────────────────
NTP_SERVER         = os.getenv('NTP_SERVER', 'time.google.com')
NTP_PORT           = int(os.getenv('NTP_PORT', '123'))
NTP_SYNC_INTERVAL  = int(os.getenv('NTP_SYNC_INTERVAL', '60'))     # minutos
HIK_TIMEZONE       = os.getenv('HIK_TIMEZONE', 'CST+6:00:00')      # UTC-6 Nicaragua

# ── Conexión a DVRs ───────────────────────────────────────────
TIMEOUT_SEGUNDOS   = int(os.getenv('TIMEOUT_SEGUNDOS', '10'))

# ── Paralelismo ───────────────────────────────────────────────
MAX_WORKERS        = int(os.getenv('MAX_WORKERS', '5'))

# ── Webhook ───────────────────────────────────────────────────
WEBHOOK_URL        = os.getenv('NTP_WEBHOOK_URL', '')              # vacío = no enviar
WEBHOOK_TOKEN      = os.getenv('NTP_WEBHOOK_TOKEN', '')            # Bearer opcional
