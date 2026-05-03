"""
preprocessor.py — Comprime el video con ffmpeg antes de enviarlo a Gemini.

Objetivo: reducir tamaño manteniendo legibilidad visual suficiente para IA.
- Resolución: 480p (ancho máximo 854, mantiene aspecto)
- FPS: 5 (suficiente para ver movimiento, mucho menor que 25-30 original)
- Video bitrate: 300 kbps
- Audio: 64 kbps mono (si existe)

Un clip de 3 minutos queda en ~6-8 MB, apto para Gemini Files API.
"""

import subprocess
import os

from . import config
from .logger import get_logger

log = get_logger('preprocessor')


def compress(input_path: str) -> str:
    """
    Comprime el video en input_path.
    Retorna la ruta del video comprimido (_small.mp4).
    Lanza Exception si falla.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Video de entrada no encontrado: {input_path}")

    base   = os.path.splitext(input_path)[0]
    output = f"{base}_small.mp4"

    log.info(f"🔧 Preprocesando: {os.path.basename(input_path)}")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        # Video: escalar a 480p, 5fps, 300kbps
        "-vf", "scale=854:-2:flags=lanczos",
        "-r", "5",
        "-c:v", "libx264",
        "-b:v", "300k",
        "-preset", "fast",
        # Audio: 64kbps mono si existe, no fallar si no hay audio
        "-c:a", "aac",
        "-b:a", "64k",
        "-ac", "1",
        # Si no hay audio, agregar silencio para evitar error
        "-f", "mp4",
        output
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout preprocesando {input_path}")

    if result.returncode != 0:
        # Puede fallar por falta de audio — reintentar sin audio
        log.warning("⚠️  Reintentando sin audio (video puede no tener pista de audio)...")
        cmd_noaudio = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", "scale=854:-2:flags=lanczos",
            "-r", "5",
            "-c:v", "libx264",
            "-b:v", "300k",
            "-preset", "fast",
            "-an",  # Sin audio
            output
        ]
        result2 = subprocess.run(cmd_noaudio, capture_output=True, text=True, timeout=300)
        if result2.returncode != 0:
            raise RuntimeError(
                f"ffmpeg preproceso falló: {result2.stderr[-500:]}"
            )

    if not os.path.exists(output) or os.path.getsize(output) < 512:
        raise RuntimeError(f"Video comprimido vacío: {output}")

    orig_mb  = os.path.getsize(input_path) / (1024 * 1024)
    small_mb = os.path.getsize(output)     / (1024 * 1024)
    log.info(f"✅ Comprimido: {small_mb:.1f} MB (original: {orig_mb:.1f} MB, reducción: {(1-small_mb/orig_mb)*100:.0f}%)")

    return output


def has_audio(video_path: str) -> bool:
    """Detecta si el video tiene pista de audio usando ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-select_streams", "a",
             "-show_entries", "stream=codec_type",
             "-of", "csv=p=0",
             video_path],
            capture_output=True, text=True, timeout=15
        )
        return 'audio' in result.stdout
    except Exception:
        return False


def get_duration_seconds(video_path: str) -> int:
    """Obtiene la duración del video en segundos usando ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "csv=p=0",
             video_path],
            capture_output=True, text=True, timeout=15
        )
        return int(float(result.stdout.strip()))
    except Exception:
        return 0
