"""
downloader.py — Descarga video del DVR vía RTSP sobre túnel SSH usando ffmpeg.

NOTA IMPORTANTE sobre timestamps Hikvision:
Los DVR HiLook/Hikvision almacenan las grabaciones indexadas por su HORA LOCAL.
Aunque el formato RTSP usa el sufijo 'Z' (UTC), el firmware de estos DVR
ignora el timezone y trata el timestamp como hora local.
Por eso se envía la hora Nicaragua directamente (sin convertir a UTC).
Enviar UTC causaba 400 Bad Request porque el DVR buscaba video en el tiempo
equivocado (ej: medianoche en lugar de 18:30).
"""

import subprocess
import os
from datetime import datetime

from . import config
from .logger import get_logger

log = get_logger('downloader')


def _parse_ni_datetime(fecha: str, hora: str) -> datetime:
    """Parsea fecha (YYYY-MM-DD) + hora (HH:MM:SS) en hora Nicaragua."""
    return datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M:%S")


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

    # Enviar hora Nicaragua directamente — el DVR HiLook ignora el sufijo Z
    # y busca la grabación por hora local del dispositivo.
    dt_ini = _parse_ni_datetime(fecha, hora_ini)
    dt_fin = _parse_ni_datetime(fecha, hora_fin)

    start_str    = dt_ini.strftime("%Y%m%dT%H%M%SZ")  # Z es formalidad, DVR usa hora local
    end_str      = dt_fin.strftime("%Y%m%dT%H%M%SZ")
    duracion_seg = max(int((dt_fin - dt_ini).total_seconds()), 10)

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
        f"local={local} {hora_ini}→{hora_fin} (hora NI local → {start_str}→{end_str}) "
        f"puerto={puerto} track={track}"
    )

    # DVR Hikvision/HiLook transmite audio en pcm_mulaw (G.711) que NO es
    # compatible con contenedor MP4. Se transcodifica a AAC (sí compatible).
    # Fallback sin audio si el codec del DVR es aún más exótico.
    def _build_cmd(audio_flags: list) -> list:
        return [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-c:v", "copy",
            *audio_flags,
            "-t", str(duracion_seg),
            ruta_salida
        ]

    intentos = [
        (["-c:a", "aac", "-b:a", "64k", "-ac", "1"], "audio AAC"),
        (["-an"],                                       "sin audio"),
    ]

    result = None
    for audio_flags, descripcion_audio in intentos:
        cmd = _build_cmd(audio_flags)
        log.info(f"   Intentando con {descripcion_audio}...")
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
        if result.returncode == 0:
            log.info(f"   ✅ Descarga exitosa ({descripcion_audio})")
            break
        log.warning(f"   ⚠️  Falló con {descripcion_audio}, probando siguiente...")

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
