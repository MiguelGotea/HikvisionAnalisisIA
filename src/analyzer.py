"""
analyzer.py — Análisis de video de atención al cliente con Gemini 2.5 Flash.

Flujo:
1. Subir video a Gemini Files API (resumable upload)
2. Esperar estado ACTIVE (Gemini procesa el video)
3. Enviar prompt de análisis con file_uri
4. Parsear respuesta JSON con calificaciones 1-10
5. Eliminar archivo de Gemini (limpieza de cuota)

Modelo: gemini-2.5-flash (v1beta, Files API para video multimodal)
"""

import requests
import json
import time
import os

from .logger import get_logger

log = get_logger('analyzer')

GEMINI_UPLOAD_URL  = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GEMINI_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# file_name retorna "files/abc123" — usar v1beta/{name} para no duplicar el prefijo
GEMINI_FILES_BASE  = "https://generativelanguage.googleapis.com/v1beta/{name}"


# ── Upload ───────────────────────────────────────────────────

def _upload_video(video_path: str, api_key: str) -> tuple[str, str]:
    """
    Sube el video a Gemini Files API (resumable upload).
    Retorna (file_uri, file_name).
    """
    file_size    = os.path.getsize(video_path)
    display_name = os.path.basename(video_path)

    log.info(f"📤 Subiendo video a Gemini ({file_size/(1024*1024):.1f} MB)...")

    # Paso 1: Iniciar upload resumable
    init_resp = requests.post(
        f"{GEMINI_UPLOAD_URL}?key={api_key}",
        headers={
            'X-Goog-Upload-Protocol': 'resumable',
            'X-Goog-Upload-Command': 'start',
            'X-Goog-Upload-Header-Content-Length': str(file_size),
            'X-Goog-Upload-Header-Content-Type': 'video/mp4',
            'Content-Type': 'application/json',
        },
        json={'file': {'display_name': display_name}},
        timeout=30
    )
    init_resp.raise_for_status()

    upload_url = init_resp.headers.get('X-Goog-Upload-URL')
    if not upload_url:
        raise RuntimeError("Gemini no devolvió upload URL en el header")

    # Paso 2: Subir bytes
    with open(video_path, 'rb') as f:
        video_bytes = f.read()

    upload_resp = requests.post(
        upload_url,
        headers={
            'Content-Length': str(file_size),
            'X-Goog-Upload-Offset': '0',
            'X-Goog-Upload-Command': 'upload, finalize',
        },
        data=video_bytes,
        timeout=120
    )
    upload_resp.raise_for_status()

    file_info = upload_resp.json()
    file_uri  = file_info.get('file', {}).get('uri')
    file_name = file_info.get('file', {}).get('name')   # "files/abc123"

    if not file_uri:
        raise RuntimeError(f"Gemini no retornó file URI. Respuesta: {file_info}")

    log.info("⏳ Video subido. Esperando procesamiento Gemini...")
    _wait_for_active(file_name, api_key)
    log.info(f"✅ Video listo en Gemini: {file_uri}")
    return file_uri, file_name


def _wait_for_active(file_name: str, api_key: str, max_wait: int = 300):
    """
    Espera hasta que el archivo esté ACTIVE.
    GET /v1beta/{file_name} retorna el File object directamente (state en raíz, no en 'file').
    """
    deadline     = time.time() + max_wait
    ultimo_estado = ''
    while time.time() < deadline:
        try:
            resp = requests.get(
                GEMINI_FILES_BASE.format(name=file_name),
                params={'key': api_key},
                timeout=15
            )
            if resp.status_code == 200:
                state = resp.json().get('state', '')
                if state != ultimo_estado:
                    log.info(f"   Gemini estado: {state}")
                    ultimo_estado = state
                if state == 'ACTIVE':
                    return
                if state == 'FAILED':
                    raise RuntimeError(f"Gemini FAILED al procesar el video.")
            else:
                log.warning(f"   Polling Gemini HTTP {resp.status_code}")
        except RuntimeError:
            raise
        except Exception as e:
            log.warning(f"   Error en polling: {e}")
        time.sleep(5)
    raise RuntimeError(f"Timeout ({max_wait}s) esperando que Gemini procese el video.")


def _delete_gemini_file(file_name: str, api_key: str):
    """Elimina el archivo de Gemini para liberar cuota (48h de expiración de todos modos)."""
    try:
        requests.delete(
            GEMINI_FILES_BASE.format(name=file_name),
            params={'key': api_key},
            timeout=15
        )
        log.info(f"🗑️  Archivo Gemini eliminado: {file_name}")
    except Exception as e:
        log.warning(f"No se pudo eliminar archivo Gemini {file_name}: {e}")


# ── Prompts ───────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un evaluador experto en atención al cliente para una cadena de batidos y bebidas naturales.
Analizarás un clip de video de cámara de seguridad de una caja registradora.
Tu tarea es evaluar la calidad de atención al cliente del personal.

Responde ÚNICAMENTE con un JSON válido, sin markdown, sin texto adicional."""

USER_PROMPT_TEMPLATE = """Analiza este video de cámara de seguridad de la caja registradora.
Sucursal: {sucursal}
Fecha/hora Nicaragua: {fecha} {hora_inicio} → {hora_fin}
Video tiene audio: {tiene_audio}

Evalúa al empleado en las siguientes categorías con una calificación del 1 al 10:
- amabilidad: ¿El trato al cliente fue amable, sonriente y respetuoso?
- saludo: ¿Saludó al cliente al acercarse a la caja?
- despedida: ¿Se despidió del cliente al finalizar la atención?
- oferta_membresia: ¿Ofreció o mencionó el programa de membresía/puntos del club?

Si el video no muestra claramente una interacción cliente-empleado, asigna null a esa categoría.

Responde SOLO con este JSON (sin markdown):
{{
  "cal_amabilidad": <1-10 o null>,
  "cal_saludo": <1-10 o null>,
  "cal_despedida": <1-10 o null>,
  "cal_membresia": <1-10 o null>,
  "resumen": "<2-3 oraciones describiendo la interacción observada>",
  "tiene_audio": <true o false según lo que percibiste>
}}"""


# ── Análisis principal ────────────────────────────────────────

def analyze(video_path: str, gemini_key_info: dict, item: dict, tiene_audio: bool = False) -> dict:
    """
    Analiza el video con Gemini y retorna el dict con resultados.

    gemini_key_info: {'api_key': '...', 'modelo': 'gemini-2.5-flash', ...}
    item: item de la cola con fecha, hora_inicio, hora_fin, local_codigo, etc.
    """
    api_key = gemini_key_info['api_key']
    modelo  = gemini_key_info.get('modelo', 'gemini-2.5-flash')

    file_uri  = None
    file_name = None

    try:
        # 1. Subir video
        file_uri, file_name = _upload_video(video_path, api_key)

        # 2. Construir prompt
        sucursal_nombre = item.get('sucursal_nombre') or f"Local {item['local_codigo']}"
        user_prompt = USER_PROMPT_TEMPLATE.format(
            sucursal    = sucursal_nombre,
            fecha       = item['fecha'],
            hora_inicio = item['hora_inicio'],
            hora_fin    = item['hora_fin'],
            tiene_audio = 'Sí' if tiene_audio else 'No',
        )

        # 3. Llamar generateContent (v1beta obligatorio para file_data)
        log.info(f"🤖 Analizando con {modelo}...")
        payload = {
            'contents': [{
                'role': 'user',
                'parts': [
                    {'text': f"{SYSTEM_PROMPT}\n\n{user_prompt}"},
                    {'file_data': {'mime_type': 'video/mp4', 'file_uri': file_uri}},
                ]
            }],
            'generationConfig': {
                'temperature': 0.1,
                'maxOutputTokens': 4096,
                'response_mime_type': 'application/json',
                'thinkingConfig': {'thinkingBudget': 0},   # Dentro de generationConfig
            },
        }

        resp = requests.post(
            GEMINI_CONTENT_URL.format(model=modelo),
            params={'key': api_key},
            json=payload,
            timeout=90
        )
        resp.raise_for_status()

        # 4. Parsear respuesta
        content = resp.json()
        texto   = content['candidates'][0]['content']['parts'][0]['text']
        datos   = _parse_json_safe(texto)

        # 5. Normalizar calificaciones
        resultado = {
            'cal_amabilidad' : _validar_cal(datos.get('cal_amabilidad')),
            'cal_saludo'     : _validar_cal(datos.get('cal_saludo')),
            'cal_despedida'  : _validar_cal(datos.get('cal_despedida')),
            'cal_membresia'  : _validar_cal(datos.get('cal_membresia')),
            'resumen'        : str(datos.get('resumen', ''))[:2000],
            'tiene_audio'    : 1 if datos.get('tiene_audio') else int(tiene_audio),
            'modelo_ia'      : modelo,
        }

        log.info(
            f"✅ Análisis completado. Calificaciones: "
            f"amabilidad={resultado['cal_amabilidad']} "
            f"saludo={resultado['cal_saludo']} "
            f"despedida={resultado['cal_despedida']} "
            f"membresía={resultado['cal_membresia']}"
        )
        return resultado

    finally:
        if file_name:
            _delete_gemini_file(file_name, api_key)


# ── Helpers ───────────────────────────────────────────────────

def _validar_cal(valor) -> int | None:
    """Valida y normaliza calificación 1-10."""
    if valor is None:
        return None
    try:
        v = int(valor)
        return max(1, min(10, v))
    except (TypeError, ValueError):
        return None


def _parse_json_safe(texto: str) -> dict:
    """Extrae JSON de la respuesta tolerando envoltorios markdown."""
    texto = texto.strip()
    if texto.startswith('```'):
        lines = texto.split('\n')
        texto = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini retornó JSON inválido: {e}. Raw: {texto[:400]}")
