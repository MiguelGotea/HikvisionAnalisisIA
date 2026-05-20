"""
logger.py — Logger centralizado con salida a consola (stdout) y archivo rotativo.
Sigue el mismo patrón que src/logger.py del proyecto principal pero añade
RotatingFileHandler con 5 MB máx y 3 backups.
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR  = os.path.join(os.path.dirname(__file__), 'logs')
_LOG_FILE = os.path.join(_LOG_DIR, 'ntp_setup.log')

os.makedirs(_LOG_DIR, exist_ok=True)

_fmt = logging.Formatter(
    fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def _build_handlers() -> list:
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(_fmt)

    rotative = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding='utf-8',
    )
    rotative.setFormatter(_fmt)
    return [console, rotative]


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        for h in _build_handlers():
            logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger
