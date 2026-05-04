#!/usr/bin/env python3
"""
diagnostico_rtsp.py — Diagnóstico completo de conectividad RTSP con el DVR.

Uso:
  python scripts/diagnostico_rtsp.py --local 16
  python scripts/diagnostico_rtsp.py --local 16 --fecha 2026-05-03 --hora-ini 17:27:52 --hora-fin 17:29:23
  python scripts/diagnostico_rtsp.py --local 16 --probar-ahora   # prueba con tiempo LIVE
  python scripts/diagnostico_rtsp.py --help
"""

import sys
import os
import subprocess
import argparse
import socket
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import config
from src.logger import get_logger

log = get_logger('diagnostico_rtsp')


def probar_puerto(host: str, puerto: int, timeout: float = 5.0) -> bool:
    """Verifica si el puerto TCP está abierto (túnel SSH activo)."""
    try:
        sock = socket.create_connection((host, puerto), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def obtener_info_local(local_codigo: str) -> dict | None:
    """Obtiene los datos de conexión del local desde la API."""
    import requests
    headers = {'X-WSP-Token': config.API_TOKEN}
    # Buscar un item de prueba en la cola para obtener datos del local,
    # o bien llamar directamente al endpoint de configuración si existe.
    url = f"{config.API_BASE_URL}/obtener_item_cola.php"
    try:
        r = requests.get(url, headers=headers, params={'local': local_codigo}, timeout=15)
        if r.status_code == 200:
            resp = r.json()
            if resp.get('item'):
                return resp['item']
    except Exception as e:
        log.warning(f"No se pudo consultar obtener_item_cola.php: {e}")
    return None


def probar_rtsp_url(rtsp_url: str, duracion: int, timeout_extra: int = 15, modo: str = "tcp") -> dict:
    """
    Intenta descargar 'duracion' segundos del stream RTSP.
    Retorna {'ok': bool, 'returncode': int, 'stderr': str, 'duracion_ms': int}
    """
    out_path = "/tmp/diag_test.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-rtsp_transport", modo,
        "-timeout", "20000000",        # 20s timeout RTSP (ffmpeg 6.x)
        "-i", rtsp_url,
        "-an",
        "-c:v", "copy",
        "-t", str(duracion),
        out_path
    ]
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duracion + timeout_extra
        )
        elapsed_ms = int((time.time() - t0) * 1000)
        ok = result.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 1024
        return {
            'ok': ok,
            'returncode': result.returncode,
            'stderr': result.stderr,
            'duracion_ms': elapsed_ms,
        }
    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.time() - t0) * 1000)
        return {
            'ok': False,
            'returncode': -1,
            'stderr': f'Timeout tras {duracion + timeout_extra}s',
            'duracion_ms': elapsed_ms,
        }
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def main():
    parser = argparse.ArgumentParser(description='Diagnóstico RTSP para DVR Hikvision/HiLook')
    parser.add_argument('--local',     required=True,          help='Código del local (ej: 16)')
    parser.add_argument('--host',      default=config.VPS_IP,  help=f'IP del VPS (default: {config.VPS_IP})')
    parser.add_argument('--puerto',    type=int, default=None,  help='Puerto RTSP (si no se especifica, se obtiene de la API)')
    parser.add_argument('--track',     type=int, default=101,   help='Track del canal (default: 101)')
    parser.add_argument('--usuario',   default=None,            help='Usuario DVR (si no se especifica, se obtiene de la API)')
    parser.add_argument('--clave',     default=None,            help='Clave DVR (si no se especifica, se obtiene de la API)')
    parser.add_argument('--fecha',     default=None,            help='Fecha grabación YYYY-MM-DD')
    parser.add_argument('--hora-ini',  default=None,            help='Hora inicio HH:MM:SS')
    parser.add_argument('--hora-fin',  default=None,            help='Hora fin HH:MM:SS')
    parser.add_argument('--probar-ahora', action='store_true',  help='Prueba LIVE (stream en vivo, sin rango de tiempo)')
    parser.add_argument('--duracion-live', type=int, default=5, help='Segundos a capturar en modo live (default: 5)')
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("🔬 DIAGNÓSTICO RTSP HIKVISION")
    log.info("=" * 60)

    # --- Obtener credenciales ---
    host    = args.host
    puerto  = args.puerto
    track   = args.track
    usuario = args.usuario
    clave   = args.clave

    if not all([puerto, usuario, clave]):
        log.info(f"🔍 Consultando API para obtener datos del local {args.local}...")
        item = obtener_info_local(args.local)
        if item:
            puerto  = puerto  or item.get('puerto_rtsp')
            usuario = usuario or item.get('dvr_usuario')
            clave   = clave   or item.get('dvr_clave')
            track   = item.get('canal_track', track)
            log.info(f"   ✅ Datos obtenidos: puerto={puerto}, track={track}, usuario={usuario}")
        else:
            log.warning("   ⚠️  No se pudo obtener datos del local via API.")
            if not puerto:
                log.error("   ❌ Debes pasar --puerto manualmente.")
                sys.exit(1)

    log.info("")

    # --- PASO 1: Verificar puerto TCP (túnel SSH) ---
    log.info(f"🔌 PASO 1: Verificando puerto {puerto} en {host}...")
    if probar_puerto(host, puerto):
        log.info(f"   ✅ Puerto {puerto} ABIERTO — túnel SSH activo")
    else:
        log.error(f"   ❌ Puerto {puerto} CERRADO — el túnel SSH NO está activo en local {args.local}")
        log.error("   → Verifica que el script de túnel esté corriendo en el equipo del local.")
        sys.exit(1)

    log.info("")

    # --- PASO 2: Probar stream LIVE (sin rango de tiempo) ---
    log.info(f"📡 PASO 2: Probando stream LIVE (sin rango de tiempo)...")
    rtsp_live = f"rtsp://{usuario}:{clave}@{host}:{puerto}/PSIA/Streaming/tracks/{track}"
    log.info(f"   URL: {rtsp_live.replace(clave, '****')}")

    for modo in ["tcp", "udp"]:
        log.info(f"   Intentando modo {modo.upper()} ({args.duracion_live}s)...")
        res = probar_rtsp_url(rtsp_live, args.duracion_live, timeout_extra=20, modo=modo)
        if res['ok']:
            log.info(f"   ✅ Stream LIVE OK en modo {modo.upper()} ({res['duracion_ms']}ms)")
            break
        else:
            stderr_tail = res['stderr'][-400:].strip()
            log.warning(f"   ⚠️  Falló modo {modo.upper()} (código {res['returncode']}): {stderr_tail}")
    else:
        log.error("   ❌ Stream LIVE falló en todos los modos.")
        log.error("   → Causas posibles:")
        log.error("     1. Credenciales DVR incorrectas (usuario/clave)")
        log.error("     2. El canal/track no existe en este DVR")
        log.error("     3. El DVR no soporta PSIA/Streaming en este firmware")
        log.info("")
        log.info("   Probando URL alternativa /Streaming/Channels/...")
        rtsp_alt = f"rtsp://{usuario}:{clave}@{host}:{puerto}/Streaming/Channels/{track}"
        log.info(f"   URL alt: {rtsp_alt.replace(clave, '****')}")
        res_alt = probar_rtsp_url(rtsp_alt, args.duracion_live, timeout_extra=20)
        if res_alt['ok']:
            log.info(f"   ✅ Stream LIVE OK con URL alternativa /Streaming/Channels/{track}")
            log.info(f"   → ACTUALIZA downloader.py para usar /Streaming/Channels/ en lugar de /PSIA/Streaming/tracks/")
        else:
            log.error(f"   ❌ Ambas URLs fallaron. Verifica el firmware del DVR.")
        sys.exit(1)

    log.info("")

    # --- PASO 3: Probar grabación en rango de tiempo ---
    if args.fecha and args.hora_ini and args.hora_fin:
        log.info(f"🎬 PASO 3: Probando descarga de grabación {args.fecha} {args.hora_ini}→{args.hora_fin}...")
        dt_ini = datetime.strptime(f"{args.fecha} {args.hora_ini}", "%Y-%m-%d %H:%M:%S")
        dt_fin = datetime.strptime(f"{args.fecha} {args.hora_fin}", "%Y-%m-%d %H:%M:%S")
        duracion = max(int((dt_fin - dt_ini).total_seconds()), 10)

        start_str = dt_ini.strftime("%Y%m%dT%H%M%SZ")
        end_str   = dt_fin.strftime("%Y%m%dT%H%M%SZ")

        rtsp_grabacion = (
            f"rtsp://{usuario}:{clave}@{host}:{puerto}"
            f"/PSIA/Streaming/tracks/{track}"
            f"?starttime={start_str}&endtime={end_str}"
        )
        log.info(f"   URL: {rtsp_grabacion.replace(clave, '****')}")

        res = probar_rtsp_url(rtsp_grabacion, duracion, timeout_extra=30)
        if res['ok']:
            log.info(f"   ✅ Grabación encontrada y descargada ({res['duracion_ms']}ms)")
        else:
            log.warning(f"   ⚠️  Falló (código {res['returncode']}). Probando rangos alternativos...")

            # Probar ±5 minutos antes y después
            for delta_ini, delta_fin, label in [
                (-5,  5, "-5min inicio, +5min fin"),
                (-10, 0, "-10min inicio"),
                (  0, 10, "+10min fin"),
            ]:
                dt_ini2 = dt_ini + timedelta(minutes=delta_ini)
                dt_fin2 = dt_fin + timedelta(minutes=delta_fin)
                start2 = dt_ini2.strftime("%Y%m%dT%H%M%SZ")
                end2   = dt_fin2.strftime("%Y%m%dT%H%M%SZ")
                dur2   = max(int((dt_fin2 - dt_ini2).total_seconds()), 10)
                url2 = (
                    f"rtsp://{usuario}:{clave}@{host}:{puerto}"
                    f"/PSIA/Streaming/tracks/{track}"
                    f"?starttime={start2}&endtime={end2}"
                )
                log.info(f"   Probando {label} ({start2}→{end2})...")
                res2 = probar_rtsp_url(url2, min(dur2, 15), timeout_extra=25)
                if res2['ok']:
                    log.info(f"   ✅ ¡Grabación encontrada con rango ampliado: {label}!")
                    log.info(f"   → El DVR SÍ tiene video, pero el rango exacto del pedido puede no tener grabación.")
                    log.info(f"   → Considera ampliar el margen de tiempo en tu sistema (config FFMPEG_TIMEOUT_EXTRA).")
                    break
            else:
                log.error("   ❌ No se encontró grabación en ningún rango de tiempo.")
                log.error("   → Causas posibles:")
                log.error("     1. El DVR no grabó en ese horario (sin movimiento, disco lleno, o cámara desconectada)")
                log.error("     2. La zona horaria del DVR difiere de la hora del pedido")
                log.error("     3. El track no corresponde al canal con grabación")
    elif args.probar_ahora:
        log.info("📡 PASO 3: Modo --probar-ahora — solo se verificó el stream live (PASO 2).")
    else:
        log.info("ℹ️  PASO 3 omitido — pasa --fecha, --hora-ini y --hora-fin para probar grabación.")

    log.info("")
    log.info("=" * 60)
    log.info("✅ Diagnóstico completado.")
    log.info("=" * 60)


if __name__ == '__main__':
    main()
