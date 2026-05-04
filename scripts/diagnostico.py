#!/usr/bin/env python3
"""
diagnostico.py — Diagnóstico del sistema HikvisionAnalisisIA.

Consulta el estado real de la cola y los resultados sin necesidad del worker.
Útil para depurar cuando el flujo no funciona como se espera.

Uso:
  python scripts/diagnostico.py
  python scripts/diagnostico.py --id-cola 33
"""

import sys
import os
import argparse
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src import config
from src.logger import get_logger

log = get_logger('diagnostico')

HEADERS = {
    'X-WSP-Token': config.API_TOKEN,
    'Content-Type': 'application/json',
}


def check_worker_status():
    """Consulta worker_status.php para ver el estado general del sistema."""
    log.info("=== ESTADO GENERAL DEL WORKER ===")
    try:
        r = requests.get(
            f"{config.API_BASE_URL}/worker_status.php",
            headers=HEADERS, timeout=15
        )
        r.raise_for_status()
        data = r.json()

        # Cola pendiente
        cola = data.get('cola', {})
        log.info(f"  Pendientes hoy    : {cola.get('pendientes_hoy', 'N/A')}")
        log.info(f"  Procesando        : {cola.get('procesando', 'N/A')}")
        log.info(f"  Completados hoy   : {cola.get('completados_hoy', 'N/A')}")
        log.info(f"  Fallidos hoy      : {cola.get('fallidos_hoy', 'N/A')}")

        # Worker flag
        worker = data.get('worker', {})
        log.info(f"  Worker habilitado : {worker.get('habilitado', 'N/A')}")
        log.info(f"  Worker status     : {worker.get('estado', 'N/A')}")

        return data
    except Exception as e:
        log.error(f"Error consultando worker_status.php: {e}")
        return None


def check_item_cola(id_cola: int):
    """Consulta un item específico de la cola por id."""
    log.info(f"\n=== ITEM COLA id={id_cola} ===")
    try:
        r = requests.get(
            f"{config.API_BASE_URL}/obtener_item_cola.php",
            headers=HEADERS, params={'id': id_cola}, timeout=15
        )
        if r.status_code == 404:
            log.error(f"  ❌ Item {id_cola} NO EXISTE en hikvision_cola_analisis")
            log.error("     → El INSERT de encolar_pedido.php falló silenciosamente")
            log.error("     → Verifica en Hostinger: SELECT * FROM hikvision_cola_analisis ORDER BY id DESC LIMIT 5")
            return None

        r.raise_for_status()
        data = r.json()
        item = data.get('item', {})

        log.info(f"  ✅ Item encontrado")
        log.info(f"  Estado     : {item.get('estado')}")
        log.info(f"  Tipo       : {item.get('tipo')}")
        log.info(f"  Pedido     : {item.get('cod_pedido')} | Local: {item.get('local_codigo')}")
        log.info(f"  Fecha      : {item.get('fecha')}")
        log.info(f"  Horario    : {item.get('hora_inicio')} → {item.get('hora_fin')}")
        log.info(f"  Puerto DVR : {item.get('puerto_rtsp')} | Canal: {item.get('canal_track')}")
        log.info(f"  DVR IP     : {item.get('dvr_ip_local')}")
        log.info(f"  Created    : {item.get('created_at')}")
        log.info(f"  Updated    : {item.get('updated_at')}")
        return item
    except Exception as e:
        log.error(f"Error consultando item {id_cola}: {e}")
        return None


def check_api_connectivity():
    """Verifica conectividad con los endpoints principales."""
    log.info("\n=== CONECTIVIDAD API ===")
    endpoints = [
        ('worker_status.php', 'GET'),
        ('gemini_key.php',    'GET'),
        ('pedidos_cola.php',  'GET'),
    ]
    for ep, method in endpoints:
        try:
            url = f"{config.API_BASE_URL}/{ep}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            estado = '✅' if r.status_code < 400 else '❌'
            log.info(f"  {estado} {method} {ep} → HTTP {r.status_code}")
        except Exception as e:
            log.error(f"  ❌ {method} {ep} → ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description='Diagnóstico HikvisionAnalisisIA')
    parser.add_argument('--id-cola', type=int, default=None,
                        help='Verificar un item específico de la cola por su id')
    args = parser.parse_args()

    log.info(f"🔧 API: {config.API_BASE_URL}")

    check_api_connectivity()
    check_worker_status()

    if args.id_cola:
        item = check_item_cola(args.id_cola)
        if item and item.get('estado') == 'procesando':
            log.warning(f"\n⚠️  El item {args.id_cola} está en estado 'procesando'.")
            log.warning("   Esto significa que pedidos_cola.php ya lo tomó pero el worker no lo completó.")
            log.warning("   Para reprocesarlo manualmente, usa:")
            log.warning(f"   python scripts/test_manual.py --pedido {item['cod_pedido']} --local {item['local_codigo']}")
            log.warning("   (Primero resetea el estado en BD: UPDATE hikvision_cola_analisis SET estado='pendiente' WHERE id={};)".format(args.id_cola))
        elif item and item.get('estado') == 'pendiente':
            log.info(f"\n✅ Item {args.id_cola} está PENDIENTE. Puedes procesarlo con:")
            log.info(f"   python scripts/test_manual.py --pedido {item['cod_pedido']} --local {item['local_codigo']}")

    log.info("\n=== FIN DIAGNÓSTICO ===")


if __name__ == '__main__':
    main()
