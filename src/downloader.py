"""
downloader.py — Descarga video del DVR vía RTSP sobre túnel SSH usando ffmpeg.

IMPORTANTE: Las horas en la BD están en hora Nicaragua (UTC-6).
El protocolo RTSP/PSIA de Hikvision requiere timestamps en UTC.
Se suman 6 horas antes de construir la URL.
"""

import subprocess
import os
from datetime import datetime, timedelta

from . import config
from .logger import get_logger

log = get_logger('downloader')

# Offset Nicaragua → UTC
NI_TO_UTC_HOURS = 6


def _ni_time_to_utc(fecha: str, hora: str) -> datetime:
    """Convierte fecha (YYYY-MM-DD) + hora (HH:MM:SS) Nicaragua a datetime UTC."""
    dt_ni = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M:%S")
    return dt_ni + timedelta(hours=NI_TO_UTC_HOURS)


def download(item: dict) -> str:
    """
    Descarga el clip de video del DVR y lo guarda en TEMP_DIR.

    item debe tener:
      id, cod_pedido, local_codigo, fecha, hora_inicio, hora_fin,
      canal_track, puerto_rtsp, dvr_usuario, dvr_clave, vps_ip

    Retorna la ruta al archivo .mp4 descargado.
    Lanza Exception si la descarga falla.
    """
    id_cola    = item['id']
    cod_pedido = item['cod_pedido']
    local      = item['local_codigo']
    fecha      = item['fecha']        # "YYYY-MM-DD"
    hora_ini   = item['hora_inicio']  # "HH:MM:SS"
    hora_fin   = item['hora_fin']     # "HH:MM:SS"
    track      = item['canal_track']  # 101, 201...
    puerto     = item['puerto_rtsp']  # 9554, 9555...
    usuario    = item['dvr_usuario']
    clave      = item['dvr_clave']
    vps_ip     = item.get('vps_ip', config.VPS_IP)

    # Convertir a UTC para la URL RTSP
    utc_ini = _ni_time_to_utc(fecha, hora_ini)
    utc_fin = _ni_time_to_utc(fecha, hora_fin)

    start_str    = utc_ini.strftime("%Y%m%dT%H%M%SZ")
    end_str      = utc_fin.strftime("%Y%m%dT%H%M%SZ")
    duracion_seg = max(int((utc_fin - utc_ini).total_seconds()), 10)

    # Construir URL RTSP (túnel VPS expone puerto del DVR)
    rtsp_url = (
        f"rtsp://{usuario}:{clave}@{vps_ip}:{puerto}"
        f"/PSIA/Streaming/tracks/{track}"
        f"?starttime={start_str}&endtime={end_str}"
    )

    # Ruta de salida (dentro de TEMP_DIR)
    nombre_archivo = f"cola_{id_cola}_pedido_{cod_pedido}_local_{local}.mp4"
    ruta_salida    = os.path.join(config.TEMP_DIR, nombre_archivo)

    timeout_total = duracion_seg + config.FFMPEG_TIMEOUT_EXTRA

    log.info(
        f"⬇️  Descargando cola={id_cola} pedido={cod_pedido} "
        f"local={local} {hora_ini}→{hora_fin} (UTC: {start_str}→{end_str}) "
        f"puerto={puerto} track={track}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-c:v", "copy",
        "-c:a", "copy",          # Copiar audio si existe
        "-t", str(duracion_seg),
        ruta_salida
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_total
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Timeout ({timeout_total}s) descargando cola={id_cola}. "
            f"¿El túnel SSH está activo en el local?"
        )

    if result.returncode != 0:
        # Extraer último fragmento relevante del stderr de ffmpeg
        stderr_resumen = result.stderr[-800:] if result.stderr else "(sin stderr)"
        raise RuntimeError(
            f"ffmpeg falló (código {result.returncode}). "
            f"¿Hay video en ese rango de tiempo? stderr: {stderr_resumen}"
        )

    if not os.path.exists(ruta_salida) or os.path.getsize(ruta_salida) < 1024:
        raise RuntimeError(
            f"Archivo descargado vacío o inexistente: {ruta_salida}. "
            f"El DVR puede no tener grabación en ese rango."
        )

    size_mb = os.path.getsize(ruta_salida) / (1024 * 1024)
    log.info(f"✅ Descargado: {ruta_salida} ({size_mb:.1f} MB)")

    return ruta_salida
