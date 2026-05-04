"""
worker.py — Daemon principal del sistema HikvisionAnalisisIA.

Loop:
  1. Consultar cola (pedidos_cola.php) → N items pendientes
  2. Por cada item (en paralelo según WORKER_CONCURRENCY):
     a. Descargar video via RTSP/ffmpeg
     b. Preprocesar (comprimir)
     c. Obtener key Gemini
     d. Analizar con Gemini
     e. Guardar resultado
     f. Limpiar archivos temporales
  3. Si no hay items → dormir POLL_INTERVAL_EMPTY segundos
  4. Si hubo items → dormir POLL_INTERVAL_ITEM segundos y repetir

Iniciar con:  python -m src.worker
O como daemon: systemd (ver systemd/hikvision-worker.service)
"""

import os
import sys
import time
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config
from . import api_client
from . import downloader
from . import preprocessor
from . import analyzer
from .logger import get_logger

log = get_logger('worker')

# Flag para apagado limpio (systemd SIGTERM)
_running = True


def _signal_handler(signum, frame):
    global _running
    log.info(f"🛑 Señal {signum} recibida. Finalizando worker limpiamente...")
    _running = False


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT,  _signal_handler)


# ── Procesamiento de un item ─────────────────────────────────

def _cleanup(*paths):
    """Elimina archivos temporales ignorando errores."""
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
                log.info(f"🗑️  Temp eliminado: {os.path.basename(p)}")
            except Exception as e:
                log.warning(f"No se pudo eliminar {p}: {e}")


def process_item(item: dict):
    """
    Procesa un único item de la cola de forma completa.
    Maneja sus propios errores y marca fallido si algo falla.
    """
    id_cola    = item['id']
    cod_pedido = item['cod_pedido']
    local      = item['local_codigo']

    log.info(f"▶️  Iniciando cola={id_cola} pedido={cod_pedido} local={local}")

    video_raw   = None
    video_small = None

    try:
        # 1. Descargar
        video_raw = downloader.download(item)

        # 2. Detectar audio y duración antes de comprimir
        tiene_audio      = preprocessor.has_audio(video_raw)
        duracion_seg     = preprocessor.get_duration_seconds(video_raw)

        # 3. Preprocesar
        video_small = preprocessor.compress(video_raw)

        # 4. Key Gemini
        gemini_info = api_client.get_gemini_key()

        # 5. Analizar
        resultado = analyzer.analyze(
            video_path        = video_small,
            gemini_key_info   = gemini_info,
            item              = item,
            tiene_audio       = tiene_audio,
            duracion_segundos = duracion_seg,
        )
        resultado['duracion_segundos'] = duracion_seg

        # 6. Guardar resultado
        api_client.save_result(id_cola, resultado)
        log.info(f"✅ COMPLETADO cola={id_cola} pedido={cod_pedido} promedio={resultado.get('cal_promedio', 'N/A')}")

    except Exception as e:
        error_msg = str(e)
        log.error(f"❌ FALLIDO cola={id_cola} pedido={cod_pedido}: {error_msg}")
        api_client.mark_failed(id_cola, error_msg)

    finally:
        _cleanup(video_raw, video_small)


# ── Loop principal ───────────────────────────────────────────

def run():
    """Loop principal del worker. Bloqueante hasta recibir señal de parada."""
    log.info(f"🚀 HikvisionAnalisisIA Worker iniciado")
    log.info(f"   Concurrencia: {config.WORKER_CONCURRENCY} worker(s)")
    log.info(f"   Poll vacío: cada {config.POLL_INTERVAL_EMPTY}s")
    log.info(f"   API: {config.API_BASE_URL}")

    with ThreadPoolExecutor(max_workers=config.WORKER_CONCURRENCY) as executor:
        while _running:
            try:
                # Pedir tantos items como workers disponibles
                items = api_client.get_next_items(limit=config.WORKER_CONCURRENCY)

                if not items:
                    log.info(f"💤 Cola vacía. Esperando {config.POLL_INTERVAL_EMPTY}s...")
                    # Espera interrumpible para responder a SIGTERM
                    for _ in range(config.POLL_INTERVAL_EMPTY):
                        if not _running:
                            break
                        time.sleep(1)
                    continue

                log.info(f"📋 {len(items)} item(s) tomados de la cola")

                # Procesar en paralelo (ThreadPoolExecutor)
                futures = {executor.submit(process_item, item): item for item in items}
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        item = futures[future]
                        log.error(f"Error no capturado en future cola={item['id']}: {e}")

                if _running:
                    time.sleep(config.POLL_INTERVAL_ITEM)

            except Exception as e:
                log.error(f"Error en loop principal: {e}")
                time.sleep(10)

    log.info("👋 Worker detenido correctamente.")


if __name__ == '__main__':
    run()
