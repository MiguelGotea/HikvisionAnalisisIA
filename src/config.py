"""
config.py — Configuración centralizada desde variables de entorno
Todos los módulos importan desde aquí, nunca leen .env directamente.
"""

import os
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Variable de entorno requerida no definida: {key}")
    return val


# ── API ──────────────────────────────────────────────────────
API_TOKEN    = _require('HIK_API_TOKEN')
API_BASE_URL = os.getenv('HIK_API_BASE_URL', 'https://api.batidospitaya.com/api/hikvision').rstrip('/')

# ── VPS ──────────────────────────────────────────────────────
VPS_IP = os.getenv('VPS_IP', '198.211.97.243')

# ── Archivos temporales ──────────────────────────────────────
TEMP_DIR = os.getenv('TEMP_DIR', '/opt/hikvision-ia/temp')
os.makedirs(TEMP_DIR, exist_ok=True)

# ── Worker ───────────────────────────────────────────────────
WORKER_CONCURRENCY    = int(os.getenv('WORKER_CONCURRENCY', '1'))
POLL_INTERVAL_EMPTY   = int(os.getenv('POLL_INTERVAL_EMPTY', '30'))
POLL_INTERVAL_ITEM    = int(os.getenv('POLL_INTERVAL_ITEM', '5'))
FFMPEG_TIMEOUT_EXTRA  = int(os.getenv('FFMPEG_TIMEOUT_EXTRA', '120'))
