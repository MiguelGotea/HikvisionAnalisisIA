"""
main.py — Entry point del sistema de activación NTP en DVRs Hikvision.

Uso:
  python -m dvr_ntp_setup.main                        # Todos los DVRs activos
  python -m dvr_ntp_setup.main --cod-sucursal 2       # Solo un DVR por código
  python -m dvr_ntp_setup.main --dry-run              # Simular sin cambios
  python -m dvr_ntp_setup.main --workers 10           # Más workers paralelos

Exit code:
  0 → Todos los DVRs son SUCCESS o ALREADY_OK
  1 → Alguno falló, fue UNREACHABLE o tuvo AUTH_ERROR
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

import requests

from . import config
from .db import get_dvrs_activos, get_dvr_por_codigo
from .hikvision import get_time, set_time_ntp, set_ntp_server, get_ntp_server, is_already_ok, _label
from .notifier import send_webhook
from .logger import get_logger

log = get_logger('main')

# ── Resultado por DVR ─────────────────────────────────────────

ESTADOS_OK = {'SUCCESS', 'ALREADY_OK'}


def _procesar_dvr(dvr: dict, dry_run: bool) -> Dict:
    """
    Procesa un solo DVR: verifica NTP, configura si es necesario, verifica resultado.
    Retorna un dict con el resultado para el webhook y el log final.
    """
    label    = _label(dvr)
    ip       = dvr.get('portal_ip_local', '?')
    cod      = dvr.get('cod_sucursal')
    nombre   = dvr.get('nombre_sucursal', str(cod))

    base_result = {
        'cod_sucursal':    cod,
        'nombre_sucursal': nombre,
        'ip':              ip,
        'resultado':       'FAILED',
        'error':           None,
    }

    log.info(f"[{label}] {ip} — Iniciando configuración NTP")

    # ── PASO 1: Leer estado actual ────────────────────────────
    try:
        time_info = get_time(dvr)
    except requests.exceptions.ConnectionError as exc:
        msg = f"Connection error: {exc}"
        log.warning(f"[{label}] {ip} — UNREACHABLE: {msg}")
        return {**base_result, 'resultado': 'UNREACHABLE', 'error': str(exc)}
    except requests.exceptions.Timeout:
        log.warning(f"[{label}] {ip} — UNREACHABLE: Connection timeout")
        return {**base_result, 'resultado': 'UNREACHABLE', 'error': 'Connection timeout'}
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 401:
            log.error(f"[{label}] {ip} — AUTH_ERROR: credenciales inválidas")
            return {**base_result, 'resultado': 'AUTH_ERROR', 'error': '401 Unauthorized'}
        log.error(f"[{label}] {ip} — FAILED al leer /ISAPI/System/time: {exc}")
        return {**base_result, 'resultado': 'FAILED', 'error': str(exc)}
    except Exception as exc:
        log.error(f"[{label}] {ip} — FAILED (excepción inesperada): {exc}")
        return {**base_result, 'resultado': 'FAILED', 'error': str(exc)}

    log.info(f"[{label}] {ip} — timeMode actual: {time_info.time_mode!r}, timeZone: {time_info.time_zone!r}")

    # ── PASO 2: Leer estado NTP actual (para decidir si ya está OK) ───
    try:
        ntp_info = get_ntp_server(dvr)
    except Exception:
        # Si el endpoint NTP no responde, asumimos que no está configurado
        from .hikvision import NtpServerInfo
        ntp_info = NtpServerInfo()

    # ── PASO 3: Verificar si ya está correcto ─────────────────
    if is_already_ok(time_info, ntp_info):
        log.info(f"[{label}] {ip} — ALREADY_OK (NTP={ntp_info.host_name}, tz={time_info.time_zone})")
        return {**base_result, 'resultado': 'ALREADY_OK', 'error': None}

    if dry_run:
        log.info(f"[{label}] {ip} — [DRY-RUN] Se aplicaría NTP. Sin cambios.")
        return {**base_result, 'resultado': 'SUCCESS', 'error': None}

    # ── PASO 4: Configurar modo NTP + zona horaria ────────────
    steps_ok = 0
    try:
        set_time_ntp(dvr)
        steps_ok += 1
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 401:
            log.error(f"[{label}] {ip} — AUTH_ERROR en PUT /ISAPI/System/time")
            return {**base_result, 'resultado': 'AUTH_ERROR', 'error': '401 en PUT time'}
        log.error(f"[{label}] {ip} — FAILED en PUT /ISAPI/System/time: {exc}")
        return {**base_result, 'resultado': 'FAILED', 'error': f'PUT time: {exc}'}
    except Exception as exc:
        log.error(f"[{label}] {ip} — FAILED en PUT /ISAPI/System/time: {exc}")
        return {**base_result, 'resultado': 'FAILED', 'error': f'PUT time: {exc}'}

    # ── PASO 5: Configurar servidor NTP ───────────────────────
    try:
        set_ntp_server(dvr)
        steps_ok += 1
    except Exception as exc:
        log.error(f"[{label}] {ip} — PARTIAL: PUT NtpServers/1 falló: {exc}")
        return {**base_result, 'resultado': 'PARTIAL', 'error': f'PUT NtpServer: {exc}'}

    # ── PASO 6: Verificación final ────────────────────────────
    try:
        final_time  = get_time(dvr)
        final_ntp   = get_ntp_server(dvr)
        if is_already_ok(final_time, final_ntp):
            log.info(f"[{label}] {ip} — Verificación OK → SUCCESS")
            return {**base_result, 'resultado': 'SUCCESS', 'error': None}
        else:
            log.warning(
                f"[{label}] {ip} — Verificación fallida: "
                f"timeMode={final_time.time_mode!r}, "
                f"ntp={final_ntp.host_name!r}, "
                f"tz={final_time.time_zone!r}"
            )
            return {**base_result, 'resultado': 'PARTIAL', 'error': 'Verificación post-PUT discrepante'}
    except Exception as exc:
        log.error(f"[{label}] {ip} — PARTIAL: Error en verificación final: {exc}")
        return {**base_result, 'resultado': 'PARTIAL', 'error': f'Verificación: {exc}'}


# ── Orquestador principal ─────────────────────────────────────

def run(cod_sucursal: int | None, dry_run: bool, workers: int) -> List[Dict]:
    """Ejecuta el proceso completo y retorna la lista de resultados."""

    # ── Obtener lista de DVRs ─────────────────────────────────
    if cod_sucursal is not None:
        dvr = get_dvr_por_codigo(cod_sucursal)
        if dvr is None:
            raise RuntimeError(f"No se encontró DVR con cod_sucursal={cod_sucursal}")
        dvrs = [dvr]
    else:
        dvrs = get_dvrs_activos()

    log.info(f"{'[DRY-RUN] ' if dry_run else ''}Procesando {len(dvrs)} DVR(s) con {workers} worker(s)...")

    resultados: List[Dict] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_procesar_dvr, dvr, dry_run): dvr
            for dvr in dvrs
        }
        for future in as_completed(futures):
            dvr = futures[future]
            try:
                resultado = future.result()
            except Exception as exc:
                label = _label(dvr)
                log.error(f"[{label}] Excepción no capturada en worker: {exc}")
                resultado = {
                    'cod_sucursal':    dvr.get('cod_sucursal'),
                    'nombre_sucursal': dvr.get('nombre_sucursal'),
                    'ip':              dvr.get('portal_ip_local', '?'),
                    'resultado':       'FAILED',
                    'error':           str(exc),
                }
            resultados.append(resultado)

    return resultados


def _print_resumen(resultados: List[Dict]):
    """Imprime tabla resumen en consola."""
    log.info("=" * 60)
    log.info(f"{'RESUMEN FINAL':^60}")
    log.info("=" * 60)
    for r in sorted(resultados, key=lambda x: str(x.get('nombre_sucursal', ''))):
        estado = r['resultado']
        error  = f" — {r['error']}" if r.get('error') else ''
        log.info(f"  {r.get('nombre_sucursal', r.get('cod_sucursal')):.<30} {estado}{error}")
    log.info("-" * 60)
    from collections import Counter
    c = Counter(r['resultado'] for r in resultados)
    log.info(
        f"  Total: {len(resultados)} | "
        f"SUCCESS: {c['SUCCESS']} | ALREADY_OK: {c['ALREADY_OK']} | "
        f"UNREACHABLE: {c['UNREACHABLE']} | AUTH_ERROR: {c['AUTH_ERROR']} | "
        f"PARTIAL: {c['PARTIAL']} | FAILED: {c['FAILED']}"
    )
    log.info("=" * 60)


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Activa y configura NTP en DVRs Hikvision vía ISAPI.'
    )
    parser.add_argument(
        '--cod-sucursal', type=int, default=None,
        help='Procesar solo el DVR con este código de sucursal.'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Simular sin realizar cambios en los DVRs.'
    )
    parser.add_argument(
        '--workers', type=int, default=config.MAX_WORKERS,
        help=f'Workers paralelos (default: {config.MAX_WORKERS}).'
    )
    args = parser.parse_args()

    try:
        resultados = run(
            cod_sucursal=args.cod_sucursal,
            dry_run=args.dry_run,
            workers=args.workers,
        )
    except RuntimeError as exc:
        log.critical(f"Error fatal — abortando: {exc}")
        sys.exit(2)

    _print_resumen(resultados)

    # Enviar webhook (no aborta si falla)
    send_webhook(resultados)

    # Exit code
    estados_ok = {'SUCCESS', 'ALREADY_OK'}
    hay_fallo = any(r['resultado'] not in estados_ok for r in resultados)
    sys.exit(1 if hay_fallo else 0)


if __name__ == '__main__':
    main()
