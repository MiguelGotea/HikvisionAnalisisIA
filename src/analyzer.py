"""
analyzer.py — Análisis de video de atención al cliente con Gemini 2.5 Flash.

Evalúa el Protocolo Oficial de Atención Pitaya (10 pasos, 5 grupos):
  Grupo 1 — Bienvenida    (Paso 1)
  Grupo 2 — Asesoría      (Pasos 2-4, marcados * = opcional en fila larga)
  Grupo 3 — Membresía     (Paso 5)
  Grupo 4 — Cobro         (Pasos 6-8)
  Grupo 5 — Entrega       (Pasos 9-10)
"""

import requests
import json
import time
import os

from .logger import get_logger

log = get_logger('analyzer')

GEMINI_UPLOAD_URL  = "https://generativelanguage.googleapis.com/upload/v1beta/files"
GEMINI_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_FILES_BASE  = "https://generativelanguage.googleapis.com/v1beta/{name}"


# ── Upload ────────────────────────────────────────────────────

def _upload_video(video_path: str, api_key: str) -> tuple[str, str]:
    """Sube el video a Gemini Files API. Retorna (file_uri, file_name)."""
    file_size    = os.path.getsize(video_path)
    display_name = os.path.basename(video_path)

    log.info(f"📤 Subiendo video a Gemini ({file_size/(1024*1024):.1f} MB)...")

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
    file_name = file_info.get('file', {}).get('name')

    if not file_uri:
        raise RuntimeError(f"Gemini no retornó file URI. Respuesta: {file_info}")

    log.info("⏳ Video subido. Esperando procesamiento Gemini...")
    _wait_for_active(file_name, api_key)
    log.info(f"✅ Video listo en Gemini: {file_uri}")
    return file_uri, file_name


def _wait_for_active(file_name: str, api_key: str, max_wait: int = 300):
    """Espera hasta que el archivo esté ACTIVE. State está en la raíz del response."""
    deadline      = time.time() + max_wait
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
                    raise RuntimeError("Gemini FAILED al procesar el video.")
        except RuntimeError:
            raise
        except Exception as e:
            log.warning(f"   Error en polling: {e}")
        time.sleep(5)
    raise RuntimeError(f"Timeout ({max_wait}s) esperando que Gemini procese el video.")


def _delete_gemini_file(file_name: str, api_key: str):
    """Elimina el archivo de Gemini para liberar cuota."""
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

SYSTEM_PROMPT = """Eres un evaluador experto en atención al cliente de Pitaya, una cadena de batidos y bebidas naturales de Nicaragua.
Analizarás un clip de video (y audio si está disponible) de la cámara de seguridad de la caja registradora.

Tu tarea es evaluar el cumplimiento del Protocolo Oficial de Atención al Cliente de Pitaya, que tiene 10 pasos agrupados en 5 categorías.

REGLAS DE EVALUACIÓN:
- Califica cada PASO del 1 al 10, donde 10 = cumplimiento perfecto, 1 = no cumplió.
- Asigna null si el paso NO ES OBSERVABLE desde esta cámara (ej: el cliente salió del cuadro, no hay audio, la acción ocurre fuera de cámara).
- La calificación del GRUPO es el promedio de los pasos observables de ese grupo.
- El Grupo 2 (Asesoría) puede omitirse si hay una fila larga; en ese caso califícalo igualmente pero con contexto.
- Sé objetivo y basa cada calificación en evidencia observada en el video.

Responde ÚNICAMENTE con JSON válido, sin markdown ni texto adicional."""


USER_PROMPT_TEMPLATE = """Analiza el siguiente clip de video de cámara de caja registradora de Pitaya.

Sucursal: {sucursal}
Fecha y hora (Nicaragua): {fecha} de {hora_inicio} a {hora_fin}
Duración del clip: {duracion}
Audio disponible: {tiene_audio}

== PROTOCOLO DE ATENCIÓN PITAYA (10 pasos) ==

GRUPO 1 — BIENVENIDA (Paso 1):
  paso_1_saludo_inmediato: ¿Saludó de forma inmediata al entrar el cliente?
  paso_1_sonrisa_contacto: ¿Con sonrisa genuina y contacto visual?
  paso_1_energia_positiva: ¿Transmitió energía positiva y cercanía?

GRUPO 2 — ASESORÍA Y VENTA (Pasos 2-4) — marcado con (*), puede omitirse en fila larga:
  paso_2_escucha_activa:  ¿Escuchó activamente al cliente e identificó sus necesidades?
  paso_2_recomendo:       ¿Recomendó productos o la promoción/combo de temporada?
  paso_3_personalizo:     ¿Ofreció opciones de personalización (endulzante, toppings de waffles)?
  paso_4_acompanante:     ¿Sugirió un acompañante (galletas de avena, frutos secos Pitaya) o promoción vigente sin presionar?

GRUPO 3 — MEMBRESÍA CLUB PITAYA (Paso 5) — {membresia_instruccion}:
  paso_5_pregunto_membresia:  ¿Preguntó si el cliente tiene membresía del Club Pitaya?
  paso_5_explico_beneficios:  ¿Explicó brevemente los beneficios si el cliente no tenía membresía?

GRUPO 4 — PROCESO DE COBRO (Pasos 6-8):
  paso_6_pidio_nombre:    ¿Solicitó el nombre del cliente para la orden?
  paso_6_indico_monto:    ¿Indicó el monto total y los métodos de pago disponibles?
  paso_7_repitio_orden:   ¿Repitió exactamente la orden del cliente para confirmar?
  paso_8_pregunto_propina:¿Preguntó si el cliente desea agregar propina?
  paso_8b_entrego_factura:¿Entregó la factura al cliente?

GRUPO 5 — ENTREGA Y DESPEDIDA (Pasos 9-10):
  paso_9_llamo_por_nombre:  ¿Llamó al cliente por su nombre al entregar el producto?
  paso_9_menciono_producto: ¿Mencionó los productos al hacer la entrega?
  paso_9_sonrisa_entrega:   ¿Entregó el producto con sonrisa?
  paso_10_despedida_cordial:¿Se despidió cordialmente invitando al cliente a regresar?

== RESPUESTA REQUERIDA ==

Responde SOLO con este JSON (sin markdown, valores exactos):
{{
  "grupos": {{
    "bienvenida": {{
      "cal_grupo": <1-10 promedio observable o null>,
      "pasos": {{
        "paso_1_saludo_inmediato": {{"cal": <1-10 o null>, "obs": "<observación breve en español>"}},
        "paso_1_sonrisa_contacto": {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_1_energia_positiva": {{"cal": <1-10 o null>, "obs": "<observación breve>"}}
      }}
    }},
    "asesoria": {{
      "cal_grupo": <1-10 o null>,
      "pasos": {{
        "paso_2_escucha_activa":  {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_2_recomendo":       {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_3_personalizo":     {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_4_acompanante":     {{"cal": <1-10 o null>, "obs": "<observación breve>"}}
      }}
    }},
    "membresia": {{
      "cal_grupo": <1-10 o null>,
      "pasos": {{
        "paso_5_pregunto_membresia":  {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_5_explico_beneficios":  {{"cal": <1-10 o null>, "obs": "<observación breve>"}}
      }}
    }},
    "cobro": {{
      "cal_grupo": <1-10 o null>,
      "pasos": {{
        "paso_6_pidio_nombre":    {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_6_indico_monto":    {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_7_repitio_orden":   {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_8_pregunto_propina":{{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_8b_entrego_factura":{{"cal": <1-10 o null>, "obs": "<observación breve>"}}
      }}
    }},
    "entrega": {{
      "cal_grupo": <1-10 o null>,
      "pasos": {{
        "paso_9_llamo_por_nombre":  {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_9_menciono_producto": {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_9_sonrisa_entrega":   {{"cal": <1-10 o null>, "obs": "<observación breve>"}},
        "paso_10_despedida_cordial":{{"cal": <1-10 o null>, "obs": "<observación breve>"}}
      }}
    }}
  }},
  "resumen": "<3-4 oraciones describiendo el desempeño general, puntos fuertes y áreas de mejora>",
  "tiene_audio": <true o false según lo que percibiste>
}}"""

# Instrucciones de membresía por contexto
_MEMBRESIA_INSTRUCCION = {
    'sin_membresia': 'EVALUAR NORMALMENTE — el cliente no tiene membresía, verificar si el empleado la ofreció',
    'vendida':       'AUTO-CALIFICADO 10 — el empleado vendió la membresía en este pedido (incluir en JSON con cal_grupo=10)',
    'ya_tenia':      'NO APLICA — el cliente ya tenía membresía, asignar null a todos los pasos de este grupo',
}


# ── Análisis principal ────────────────────────────────────────

def analyze(video_path: str, gemini_key_info: dict, item: dict,
            tiene_audio: bool = False, duracion_segundos: int = 0) -> dict:
    """
    Analiza el video con el Protocolo Oficial Pitaya (5 grupos, 10 pasos).
    Retorna dict con grupos, cal_promedio, detalle_json y resumen.
    """
    api_key = gemini_key_info['api_key']
    modelo  = gemini_key_info.get('modelo', 'gemini-2.5-flash')

    file_uri  = None
    file_name = None

    try:
        file_uri, file_name = _upload_video(video_path, api_key)

        sucursal_nombre     = item.get('sucursal_nombre') or f"Local {item['local_codigo']}"
        duracion_str        = f"{duracion_segundos}s" if duracion_segundos else "desconocida"
        membresia_contexto  = item.get('membresia_contexto', 'sin_membresia')
        membresia_instruccion = _MEMBRESIA_INSTRUCCION.get(membresia_contexto, _MEMBRESIA_INSTRUCCION['sin_membresia'])

        log.info(f"   Contexto membresía: {membresia_contexto}")

        user_prompt = USER_PROMPT_TEMPLATE.format(
            sucursal              = sucursal_nombre,
            fecha                 = item['fecha'],
            hora_inicio           = item['hora_inicio'],
            hora_fin              = item['hora_fin'],
            duracion              = duracion_str,
            tiene_audio           = 'Sí' if tiene_audio else 'No',
            membresia_instruccion = membresia_instruccion,
        )

        log.info(f"🤖 Analizando con {modelo} (Protocolo 5 grupos)...")
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
                'thinkingConfig': {'thinkingBudget': 0},
            },
        }

        resp = requests.post(
            GEMINI_CONTENT_URL.format(model=modelo),
            params={'key': api_key},
            json=payload,
            timeout=90
        )
        resp.raise_for_status()

        content = resp.json()
        texto   = content['candidates'][0]['content']['parts'][0]['text']
        datos   = _parse_json_safe(texto)

        # Extraer calificaciones de grupos
        grupos = datos.get('grupos', {})
        cal_bienvenida = _cal_grupo(grupos.get('bienvenida'))
        cal_asesoria   = _cal_grupo(grupos.get('asesoria'))
        cal_cobro      = _cal_grupo(grupos.get('cobro'))
        cal_entrega    = _cal_grupo(grupos.get('entrega'))

        # Membresía: aplicar regla de negocio según contexto
        if membresia_contexto == 'vendida':
            cal_membresia = 10   # Vendió membresía = la ofreció perfectamente
            log.info("   Membresía: auto 10 (vendió membresía en este pedido)")
        elif membresia_contexto == 'ya_tenia':
            cal_membresia = None  # Cliente ya tenía membresía, no aplica evaluar
            log.info("   Membresía: null (cliente ya tenía membresía, no aplica)")
        else:
            cal_membresia = _cal_grupo(grupos.get('membresia'))  # Evaluar normalmente

        # Calcular promedio solo de grupos evaluados (no-null)
        vals = [v for v in [cal_bienvenida, cal_asesoria, cal_membresia, cal_cobro, cal_entrega] if v is not None]
        cal_promedio = round(sum(vals) / len(vals), 2) if vals else None

        resultado = {
            'grupo_bienvenida'   : cal_bienvenida,
            'grupo_asesoria'     : cal_asesoria,
            'grupo_membresia'    : cal_membresia,
            'grupo_cobro'        : cal_cobro,
            'grupo_entrega'      : cal_entrega,
            'cal_promedio'       : cal_promedio,
            'membresia_contexto' : membresia_contexto,
            'detalle_json'       : json.dumps(datos, ensure_ascii=False),
            'resumen'            : str(datos.get('resumen', ''))[:2000],
            'tiene_audio'        : 1 if datos.get('tiene_audio') else int(tiene_audio),
            'modelo_ia'          : modelo,
        }

        log.info(
            f"✅ Análisis completado. Grupos: "
            f"bienvenida={cal_bienvenida} asesoría={cal_asesoria} "
            f"membresía={cal_membresia}({membresia_contexto}) cobro={cal_cobro} entrega={cal_entrega} "
            f"→ promedio={cal_promedio}"
        )
        return resultado

    finally:
        if file_name:
            _delete_gemini_file(file_name, api_key)


# ── Helpers ───────────────────────────────────────────────────

def _cal_grupo(grupo_data: dict | None) -> int | None:
    """
    Extrae la calificación de un grupo.
    Usa cal_grupo si la IA lo calculó; si no, promedia los pasos observables.
    """
    if not grupo_data:
        return None

    # Intentar usar la calificación que calculó Gemini
    cal = grupo_data.get('cal_grupo')
    if cal is not None:
        return _validar_cal(cal)

    # Calcular como promedio de pasos no-null
    pasos = grupo_data.get('pasos', {})
    vals  = [_validar_cal(p.get('cal')) for p in pasos.values() if p.get('cal') is not None]
    return round(sum(vals) / len(vals)) if vals else None


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
    """Extrae JSON tolerando envoltorios markdown."""
    texto = texto.strip()
    if texto.startswith('```'):
        lines = texto.split('\n')
        texto = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini retornó JSON inválido: {e}. Raw: {texto[:400]}")
