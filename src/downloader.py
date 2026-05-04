"""
downloader.py — Descarga video del DVR vía RTSP sobre túnel SSH usando ffmpeg.

NOTA IMPORTANTE sobre timestamps Hikvision:
Los DVR HiLook/Hikvision almacenan las grabaciones indexadas por su HORA LOCAL.
Aunque el formato RTSP usa el sufijo 'Z' (UTC), el firmware de estos DVR
ignora el timezone y trata el timestamp como hora local.
Por eso se envía la hora Nicaragua directamente (sin convertir a UTC).
Enviar UTC causaba 400 Bad Request porque el DVR buscaba video en el tiempo
equivocado (ej: medianoche en lugar de 18:30).

FALLBACK DE URL RTSP:
El error "Invalid data found" (código 183) al conectar vía RTSP significa que
el DVR rechaza el PATH de la URL — no es un problema de audio ni de codec.
Los DVR Hikvision/HiLook tienen múltiples formatos de URL según su firmware:

  ISAPI moderno (HiLook / Hikvision reciente):
    /Streaming/Channels/101?starttime=...&endtime=...

  PSIA clásico (Hikvision firmware antiguo):
    /PSIA/Streaming/tracks/101?starttime=...&endtime=...

El downloader prueba cada formato en orden hasta encontrar el que funciona.
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
    Lanza RuntimeError si la descarga falla con todos los formatos.
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

    # Hora Nicaragua directamente — el DVR HiLook ignora el sufijo Z
    dt_ini = _parse_ni_datetime(fecha, hora_ini)
    dt_fin = _parse_ni_datetime(fecha, hora_fin)

    start_str    = dt_ini.strftime("%Y%m%dT%H%M%SZ")
    end_str      = dt_fin.strftime("%Y%m%dT%H%M%SZ")
    duracion_seg = max(int((dt_fin - dt_ini).total_seconds()), 10)

    # Ruta de salida
    nombre_archivo = f"cola_{id_cola}_pedido_{cod_pedido}_local_{local}.mp4"
    ruta_salida    = os.path.join(config.TEMP_DIR, nombre_archivo)

    timeout_total = duracion_seg + config.FFMPEG_TIMEOUT_EXTRA

    log.info(
        f"⬇️  Descargando cola={id_cola} pedido={cod_pedido} "
        f"local={local} {hora_ini}→{hora_fin} "
        f"(hora NI local → {start_str}→{end_str}) "
        f"puerto={puerto} track={track}"
    )

    # canal_simple: primer dígito del track (101 → 1, 201 → 2)
    canal_simple = int(str(track)[0]) if str(track).isdigit() else 1

    base  = f"rtsp://{usuario}:{clave}@{vps_ip}:{puerto}"
    rango = f"?starttime={start_str}&endtime={end_str}"

    # Formatos de URL RTSP a probar en orden.
    # Los DVR HiLook modernos usan ISAPI (/Streaming/Channels/).
    # Los DVR Hikvision antiguos usan PSIA (/PSIA/Streaming/tracks/).
    urls_a_probar = [
        (f"{base}/Streaming/Channels/{track}{rango}",           "ISAPI /Channels/track"),
        (f"{base}/Streaming/Channels/{canal_simple}{rango}",    "ISAPI /Channels/simple"),
        (f"{base}/PSIA/Streaming/tracks/{track}{rango}",        "PSIA /tracks/track"),
        (f"{base}/PSIA/Streaming/tracks/{canal_simple}{rango}", "PSIA /tracks/simple"),
    ]

    def _run_ffmpeg(url: str, transport: str = "tcp"):
        """Llama ffmpeg para descargar el clip RTSP. Retorna CompletedProcess."""
        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", transport,
            "-i", url,
            "-an",           # pcm_mulaw (G.711) no es compatible con MP4
            "-c:v", "copy",
            "-t", str(duracion_seg),
            ruta_salida
        ]
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_total
            )
        except subprocess.TimeoutExpired:
            log.warning(f"   ⚠️  Timeout ({timeout_total}s) — {url}")

            class _TimeoutResult:
                returncode = -1
                stderr = f"Timeout tras {timeout_total}s"

            return _TimeoutResult()

    result      = None
    url_exitosa = None

    for rtsp_url_intento, descripcion in urls_a_probar:
        log.info(f"   🔗 Probando {descripcion}...")
        result = _run_ffmpeg(rtsp_url_intento, transport="tcp")

        if result.returncode == 0:
            url_exitosa = rtsp_url_intento
            log.info(f"   ✅ Descarga exitosa con {descripcion}")
            break

        stderr_tail = (result.stderr or "")[-200:].strip()
        log.warning(
            f"   ⚠️  Falló {descripcion} "
            f"(código {result.returncode}): {stderr_tail}"
        )

        # Código 183 = "Invalid data found" → el PATH no existe en este DVR.
        # No tiene sentido reintentar con UDP; pasar al siguiente formato.
        if result.returncode == 183:
            continue

        # Para otros códigos de error, probar también con UDP
        result_udp = _run_ffmpeg(rtsp_url_intento, transport="udp")
        if result_udp.returncode == 0:
            url_exitosa = rtsp_url_intento
            log.info(f"   ✅ Descarga exitosa con {descripcion} (UDP)")
            result = result_udp
            break
        log.warning(f"   ⚠️  Falló {descripcion} UDP (código {result_udp.returncode})")

    if not url_exitosa:
        stderr_completo = result.stderr if result else "(sin resultado)"
        urls_lista = "\n".join(f"  - {d}" for _, d in urls_a_probar)
        log.error(
            f"   ❌ Todos los formatos de URL RTSP fallaron.\n"
            f"   Probados:\n{urls_lista}\n"
            f"   Último stderr: {stderr_completo[-600:]}"
        )
        raise RuntimeError(
            f"ffmpeg falló con todos los formatos de URL RTSP. "
            f"Verifica que el túnel SSH esté activo y las credenciales del DVR sean correctas. "
            f"Formatos probados: {[d for _, d in urls_a_probar]}"
        )

    if not os.path.exists(ruta_salida) or os.path.getsize(ruta_salida) < 1024:
        raise RuntimeError(
            f"Archivo descargado vacío o inexistente: {ruta_salida}. "
            f"El DVR puede no tener grabación en ese rango horario."
        )

    size_mb = os.path.getsize(ruta_salida) / (1024 * 1024)
    log.info(f"✅ Descargado: {ruta_salida} ({size_mb:.1f} MB) — URL: {url_exitosa}")

    return ruta_salida
