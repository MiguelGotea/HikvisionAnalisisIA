"""
snapshot_server.py — Servidor HTTP minimo para captura de fotogramas via ffmpeg/RTSP.

Corre en el VPS junto al worker. Acepta peticiones del ERP para capturar
un frame de cualquier camara a traves del tunel SSH activo.

Puerto: SNAPSHOT_PORT (default 8765)
Token:  HIK_API_TOKEN (mismo del worker)

POST /snapshot
  Headers: X-WSP-Token: <token>
  Body JSON: {
    "usuario":     "admin",
    "clave":       "Nihonk03",
    "puerto_rtsp": 9579,
    "canal":       101,
    "vps_ip":      "127.0.0.1"   (opcional)
  }
  Response exito:  Content-Type: image/jpeg  + bytes JPEG
  Response error:  Content-Type: application/json + {"success": false, "message": "..."}

GET /health
  Response: {"status": "ok", "service": "hikvision-snapshot"}
"""

import json
import os
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import config
from .logger import get_logger

log = get_logger('snapshot_server')

SNAPSHOT_PORT = int(os.getenv('SNAPSHOT_PORT', '8765'))
FFMPEG_TIMEOUT = 20  # segundos maximos para capturar un frame


def _capture_frame(usuario: str, clave: str, puerto_rtsp: int,
                   canal: int, vps_ip: str = '127.0.0.1') -> bytes:
    """
    Captura un fotograma JPEG del DVR via RTSP usando ffmpeg.
    Usa /Streaming/Channels/ (stream EN VIVO) para obtener la imagen
    del momento actual, no de grabaciones almacenadas.
    Canal: 101=cam1, 201=cam2, 301=cam3, 401=cam4
    Retorna los bytes del JPEG o lanza RuntimeError si falla.
    """
    # URL para este DVR (DS-7104HGHI-M1)
    # /PSIA/Streaming/tracks/X sin starttime = stream en VIVO
    # /Streaming/Channels/X no funciona en este modelo
    rtsp_url = (
        f"rtsp://{usuario}:{clave}@{vps_ip}:{puerto_rtsp}"
        f"/PSIA/Streaming/tracks/{canal}"
    )

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            'ffmpeg', '-y',
            '-rtsp_transport', 'tcp',
            '-i', rtsp_url,
            '-frames:v', '1',
            '-update', '1',          # necesario para imagen unica sin patron %d
            '-q:v', '3',             # calidad JPEG (1=mejor, 31=peor)
            tmp_path
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT
        )

        if result.returncode != 0:
            stderr = result.stderr[-600:] if result.stderr else '(sin stderr)'
            raise RuntimeError(f'ffmpeg error (cod {result.returncode}): {stderr}')

        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 1024:
            raise RuntimeError('El fotograma capturado esta vacio o es invalido.')

        with open(tmp_path, 'rb') as f:
            return f.read()

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


class SnapshotHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Redirigir logs del HTTP server a nuestro logger
        log.info(fmt % args)

    def _send_json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_jpeg(self, data: bytes):
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _check_token(self) -> bool:
        token = self.headers.get('X-WSP-Token', '')
        return token == config.API_TOKEN

    def do_GET(self):
        if self.path == '/health':
            self._send_json(200, {'status': 'ok', 'service': 'hikvision-snapshot'})
        else:
            self._send_json(404, {'success': False, 'message': 'Endpoint no encontrado'})

    def do_POST(self):
        if self.path != '/snapshot':
            self._send_json(404, {'success': False, 'message': 'Endpoint no encontrado'})
            return

        # Autenticacion
        if not self._check_token():
            self._send_json(401, {'success': False, 'message': 'Token invalido'})
            return

        # Leer body JSON
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            params = json.loads(body)
        except Exception as e:
            self._send_json(400, {'success': False, 'message': f'JSON invalido: {e}'})
            return

        usuario     = params.get('usuario', '').strip()
        clave       = params.get('clave', '').strip()
        puerto_rtsp = int(params.get('puerto_rtsp', 0))
        canal       = int(params.get('canal', 101))
        vps_ip      = params.get('vps_ip', '127.0.0.1').strip()

        if not usuario or not clave or not puerto_rtsp:
            self._send_json(400, {
                'success': False,
                'message': 'Faltan parametros: usuario, clave, puerto_rtsp'
            })
            return

        log.info(
            f'Snapshot solicitado: vps={vps_ip}:{puerto_rtsp} '
            f'canal={canal} usuario={usuario}'
        )

        try:
            jpeg_bytes = _capture_frame(usuario, clave, puerto_rtsp, canal, vps_ip)
            log.info(f'Snapshot OK: {len(jpeg_bytes) // 1024}KB')
            self._send_jpeg(jpeg_bytes)
        except subprocess.TimeoutExpired:
            msg = f'Timeout ({FFMPEG_TIMEOUT}s) capturando snapshot. Verifica que el tunel este activo.'
            log.error(msg)
            self._send_json(504, {'success': False, 'message': msg})
        except RuntimeError as e:
            log.error(f'Error snapshot: {e}')
            self._send_json(502, {'success': False, 'message': str(e)})
        except Exception as e:
            log.error(f'Error inesperado snapshot: {e}')
            self._send_json(500, {'success': False, 'message': f'Error interno: {e}'})


def run():
    server = HTTPServer(('0.0.0.0', SNAPSHOT_PORT), SnapshotHandler)
    log.info(f'Snapshot server escuchando en 0.0.0.0:{SNAPSHOT_PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info('Snapshot server detenido.')
        server.server_close()


if __name__ == '__main__':
    run()
