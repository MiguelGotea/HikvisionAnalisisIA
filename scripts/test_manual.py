#!/usr/bin/env python3
"""
test_manual.py — Herramienta de línea de comandos para probar un pedido específico.

Uso:
  python scripts/test_manual.py --pedido 12345 --local 10
  python scripts/test_manual.py --pedido 12345 --local 10 --solo-descargar
  python scripts/test_manual.py --help

El script encola el pedido como 'manual' via la API y espera el resultado.
Sirve para testear el flujo completo sin tocar el worker daemon.
"""

import sys
import os
import argparse
import time

# Agregar la raíz del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import config
from src import api_client
from src import downloader
from src import preprocessor
from src import analyzer
from src.logger import get_logger

log = get_logger('test_manual')


def encolar_y_esperar(cod_pedido: int, local: str) -> int:
    """Encola el pedido via API y retorna el id_cola."""
    import requests
    url  = f"{config.API_BASE_URL}/encolar_pedido.php"
    headers = {
        'X-WSP-Token': config.API_TOKEN,
        'Content-Type': 'application/json',
    }
    r = requests.post(url, headers=headers, json={'cod_pedido': cod_pedido, 'local': local}, timeout=15)
    r.raise_for_status()
    resp = r.json()

    if not resp.get('success'):
        raise RuntimeError(f"Error al encolar: {resp}")

    if not resp.get('encolado'):
        log.warning(f"⚠️  {resp.get('mensaje')} (id_cola={resp.get('id_cola')})")
        return resp['id_cola']

    log.info(f"✅ Encolado como manual. id_cola={resp['id_cola']}, sucursal={resp.get('sucursal')}")
    log.info(f"   Rango de tiempo: {resp.get('hora_inicio')} → {resp.get('hora_fin')}")
    return resp['id_cola']


def obtener_item_cola(id_cola: int) -> dict | None:
    """
    Obtiene un item específico de la cola por su id (sin marcarlo como procesando).
    Llama a worker_status.php que ya expone los datos del item.
    Fallback: llama a pedidos_cola.php buscando el id específico.
    """
    import requests
    headers = {'X-WSP-Token': config.API_TOKEN}

    # Intentar obtener directamente por id usando el endpoint de detalle
    url = f"{config.API_BASE_URL}/obtener_item_cola.php"
    try:
        r = requests.get(url, headers=headers, params={'id': id_cola}, timeout=15)
        if r.status_code == 200:
            resp = r.json()
            if resp.get('success') and resp.get('item'):
                return resp['item']
    except Exception:
        pass

    log.warning("obtener_item_cola.php no disponible, usando pedidos_cola.php como fallback...")
    # Fallback: pedir la cola y buscar nuestro id
    url2 = f"{config.API_BASE_URL}/pedidos_cola.php"
    r2 = requests.get(url2, headers=headers, params={'limit': 10}, timeout=15)
    r2.raise_for_status()
    items = r2.json().get('items', [])
    for it in items:
        if it['id'] == id_cola:
            return it
    return None


def procesar_directo(cod_pedido: int, local: str, solo_descargar: bool = False):
    """
    Procesa el pedido directamente (sin pasar por el worker daemon).
    Útil para debugging.
    """
    import requests

    # Obtener datos del pedido desde la cola
    log.info(f"🔍 Obteniendo datos del pedido {cod_pedido} local {local}...")

    id_cola = encolar_y_esperar(cod_pedido, local)

    # Obtener el item de cola por su id específico
    item = obtener_item_cola(id_cola)

    if not item:
        log.error(f"No se pudo obtener el item id={id_cola} de la cola.")
        log.error("Causas posibles:")
        log.error("  1. El worker ya lo tomó y marcó como 'procesando' (no sale en pedidos_cola.php)")
        log.error("  2. worker.flag.json tiene worker_habilitado=false")
        log.error("  3. La fecha del pedido no coincide con CURDATE() en la BD")
        log.error(f"  → Verifica en BD: SELECT * FROM hikvision_cola_analisis WHERE id={id_cola}")
        return

    # 1. Descargar
    log.info("\n--- PASO 1: DESCARGA ---")
    video_raw = downloader.download(item)

    if solo_descargar:
        log.info(f"✅ Video descargado en: {video_raw}")
        log.info("(--solo-descargar activado, deteniendo aquí)")
        return

    # 2. Preprocesar
    log.info("\n--- PASO 2: PREPROCESO ---")
    tiene_audio  = preprocessor.has_audio(video_raw)
    duracion_seg = preprocessor.get_duration_seconds(video_raw)
    video_small  = preprocessor.compress(video_raw)
    log.info(f"Audio detectado: {tiene_audio} | Duración: {duracion_seg}s")

    # 3. Key Gemini
    log.info("\n--- PASO 3: OBTENER KEY GEMINI ---")
    gemini_info = api_client.get_gemini_key()
    log.info(f"Modelo: {gemini_info.get('modelo')}")

    # 4. Analizar
    log.info("\n--- PASO 4: ANÁLISIS IA ---")
    resultado = analyzer.analyze(
        video_path        = video_small,
        gemini_key_info   = gemini_info,
        item              = item,
        tiene_audio       = tiene_audio,
        duracion_segundos = duracion_seg,
    )
    resultado['duracion_segundos'] = duracion_seg

    # 5. Guardar
    log.info("\n--- PASO 5: GUARDAR RESULTADO ---")
    api_client.save_result(item['id'], resultado)

    # 6. Cleanup
    for p in [video_raw, video_small]:
        if p and os.path.exists(p):
            os.remove(p)

    # Mostrar resumen — Protocolo 4 grupos (entrega/despedida no evaluable desde cámara de caja)
    log.info("\n" + "="*55)
    log.info("RESULTADO FINAL — Protocolo Pitaya (4 grupos):")
    log.info(f"  Bienvenida    : {resultado['grupo_bienvenida']}/10   (Paso 1: saludo+sonrisa)")
    log.info(f"  Asesoría      : {resultado['grupo_asesoria']}/10   (Pasos 2-4: escucha, recomienda, acompañante)")
    log.info(f"  Membresía     : {resultado['grupo_membresia']}/10   (Paso 5: Club Pitaya — ctx: {resultado.get('membresia_contexto','?')})")
    log.info(f"  Cobro         : {resultado['grupo_cobro']}/10   (Pasos 6-8: nombre, monto, repite, propina, factura)")
    log.info(f"  ─────────────────────────────────────────────")
    log.info(f"  PROMEDIO      : {resultado['cal_promedio']}/10")
    log.info(f"  Resumen       : {resultado['resumen']}")
    log.info("="*55)




def main():
    parser = argparse.ArgumentParser(
        description='Test manual de análisis de video DVR'
    )
    parser.add_argument('--pedido', type=int, required=True, help='CodPedido a analizar')
    parser.add_argument('--local',  type=str, required=True, help='Código de local (ej: 10)')
    parser.add_argument('--solo-descargar', action='store_true',
                        help='Solo descargar el video sin analizar (para depuración)')
    args = parser.parse_args()

    log.info(f"🧪 TEST MANUAL: pedido={args.pedido} local={args.local}")
    procesar_directo(args.pedido, args.local, args.solo_descargar)


if __name__ == '__main__':
    main()
