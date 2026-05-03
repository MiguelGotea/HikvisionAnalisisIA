# HikvisionAnalisisIA

Sistema automatizado de análisis de atención al cliente mediante cámaras DVR HiLook/Hikvision e Inteligencia Artificial (Gemini 2.5 Flash).

> **Estado**: ✅ Producción — Primera prueba exitosa el 2026-05-03 con sucursal Granada.

---

## Arquitectura

```
api.batidospitaya.com (Hostinger)          VPS DigitalOcean (198.211.97.243)
──────────────────────────────────         ────────────────────────────────────
api/hikvision/                             /opt/hikvision-ia/
  ├── encolar_pedido.php    ◄─ POST        src/
  ├── encolar_dia_completo.php ◄─ POST       ├── worker.py      (daemon loop)
  ├── pedidos_cola.php      ──► GET           ├── downloader.py  (RTSP/ffmpeg)
  ├── marcar_estado.php     ◄─ POST           ├── preprocessor.py(compresión)
  ├── registrar_resultado.php ◄─ POST         └── analyzer.py    (Gemini IA)
  ├── reprocesar_pedido.php ◄─ POST
  └── gemini_key.php        ──► GET

BD u839374897_erp (Hostinger)              Túneles SSH inversos (por sucursal)
  ├── VentasGlobalesAccessCSV              PC Sucursal ──► VPS:9554 ──► DVR:554
  ├── DVR_Sucursales                       (hora NI se envía directamente al DVR)
  ├── hikvision_cola_analisis
  └── hikvision_analisis_ia_atencion
```

---

## Flujo de procesamiento

```
Pedido encolado (manual o automático)
        │
        ▼
worker.py: poll cada 30s a pedidos_cola.php
        │
        ▼
downloader.py: RTSP via túnel SSH (hora Nicaragua directa, DVR la trata como local)
  rtsp://admin:PASS@198.211.97.243:9554/PSIA/Streaming/tracks/101
  ?starttime=20260502T183037Z&endtime=20260502T183209Z
  Audio pcm_mulaw (G.711) → transcodificado a AAC para MP4
        │ ~11 MB / 92 seg
        ▼
preprocessor.py: comprimir con ffmpeg
  480p | 5fps | 300kbps → ~3.7 MB (67% reducción)
        │
        ▼
analyzer.py: Gemini Files API
  Upload → PROCESSING → ACTIVE → generateContent → JSON
  Modelo: gemini-2.5-flash | maxOutputTokens: 4096
        │
        ▼
registrar_resultado.php → BD hikvision_analisis_ia_atencion
  amabilidad, saludo, despedida, membresía (1-10) + resumen
        │
        ▼
Limpiar archivos temp del VPS
```

---

## Notas técnicas importantes (lecciones del desarrollo)

| Tema | Comportamiento real |
|------|---------------------|
| **Timestamps DVR** | Los DVR HiLook/Hikvision indexan por **hora local**, ignoran el sufijo `Z`. Enviar hora Nicaragua directamente (sin convertir a UTC). |
| **Audio DVR** | El DVR transmite `pcm_mulaw` (G.711). MP4 no lo acepta en modo `copy`. Transcodificar a AAC: `-c:a aac`. |
| **Gemini Files API** | Solo funciona con `v1beta`. El campo `file_data` no existe en `v1`. |
| **Polling estado** | El GET de un archivo retorna `{"state":"ACTIVE"}` en la raíz (NO dentro de `{"file":{...}}`). |
| **URL archivos** | `file_name` ya incluye prefijo `files/`. Usar `v1beta/{file_name}` no `v1beta/files/{file_name}`. |
| **Modelo disponible** | Este key tiene Gemini 2.0/2.5 (no 1.5). Modelo confirmado: `gemini-2.5-flash`. |
| **thinkingConfig** | Va **dentro** de `generationConfig`, no en la raíz del payload. |
| **maxOutputTokens** | Usar 4096 mínimo. Con 1024 el JSON se trunca porque 2.5-flash usa tokens internamente. |

---

## Deploy

```bash
# Primer setup (solo una vez via SSH):
ssh root@198.211.97.243
mkdir -p /opt/hikvision-ia
# Hacer el primer push a main para que GitHub Actions sincronice

# Setup inicial:
cd /opt/hikvision-ia
bash scripts/setup_vps.sh
cp .env.example .env
# El .env ya tiene los valores correctos, verificar API_BASE_URL y HIK_API_TOKEN

# Después: solo push a main
git push origin main
# GitHub Actions hace rsync + systemctl restart hikvision-worker
```

### Secrets GitHub requeridos

| Secret | Valor |
|--------|-------|
| `DO_SSH_KEY` | Llave privada SSH (`id_ed25519`) |
| `DO_HOST` | `198.211.97.243` |
| `DO_USER` | `root` |
| `DO_PATH` | `/opt/hikvision-ia` |

---

## Comandos del VPS

```bash
# Iniciar el worker daemon
systemctl start hikvision-worker

# Ver estado
systemctl status hikvision-worker

# Logs en tiempo real
journalctl -u hikvision-worker -f

# Reiniciar (después de deploy manual)
systemctl restart hikvision-worker

# Test de un pedido específico
cd /opt/hikvision-ia
venv/bin/python scripts/test_manual.py --pedido XXXXX --local 10

# Solo descargar (sin analizar, para debug de RTSP)
venv/bin/python scripts/test_manual.py --pedido XXXXX --local 10 --solo-descargar

# Ver cuántos items tiene la cola
mysql -u root -p -e "SELECT estado, COUNT(*) FROM u839374897_erp.hikvision_cola_analisis GROUP BY estado;"
```

---

## Herramientas API

### Encolar pedido puntual (manual)
```http
POST https://api.batidospitaya.com/api/hikvision/encolar_pedido.php
X-WSP-Token: <token>
Content-Type: application/json

{ "cod_pedido": 12345, "local": "10" }
```

### Encolar día completo (sin delivery)
```http
POST https://api.batidospitaya.com/api/hikvision/encolar_dia_completo.php
X-WSP-Token: <token>
Content-Type: application/json

{ "fecha": "2026-05-03", "local": "10" }
```
> Omitir `local` para encolar todas las sucursales activas del día.

### Reprocesar un fallido
```http
POST https://api.batidospitaya.com/api/hikvision/reprocesar_pedido.php
X-WSP-Token: <token>
Content-Type: application/json

{ "cod_pedido": 12345, "local": "10" }
```

---

## Activar el worker daemon

```bash
# 1. Verificar que el .env tiene los valores correctos
cat /opt/hikvision-ia/.env

# 2. Registrar e iniciar el servicio
cp /opt/hikvision-ia/systemd/hikvision-worker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable hikvision-worker   # Arranque automático con el VPS
systemctl start hikvision-worker

# 3. Verificar que arrancó bien
systemctl status hikvision-worker
journalctl -u hikvision-worker -n 20

# 4. Encolar algunos pedidos de prueba
curl -s -X POST https://api.batidospitaya.com/api/hikvision/encolar_pedido.php \
  -H "X-WSP-Token: TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cod_pedido":64787,"local":"10"}'

# 5. Monitorear que el worker los procesa
journalctl -u hikvision-worker -f
```

---

## Estructura del proyecto

```
hikvisionanalisisia/
├── src/
│   ├── __init__.py
│   ├── config.py          # Variables de entorno
│   ├── logger.py          # Logger para journald
│   ├── api_client.py      # HTTP client → api.batidospitaya.com
│   ├── downloader.py      # Descarga RTSP via ffmpeg (hora NI directa)
│   ├── preprocessor.py    # Compresión 480p/5fps/300kbps (fallback sin audio)
│   ├── analyzer.py        # Gemini 2.5 Flash (Files API)
│   └── worker.py          # Daemon (ThreadPoolExecutor + SIGTERM limpio)
├── scripts/
│   ├── setup_vps.sh       # Setup inicial VPS (ejecutar 1 vez)
│   └── test_manual.py     # CLI para test de pedido específico
├── install/
│   ├── tunel_dvr_granada.bat          # Script túnel SSH Granada
│   ├── tunel_dvr_lasbrisas.bat        # Script túnel SSH Las Brisas
│   ├── setup_tarea_programada.ps1     # Crea tarea Windows como SYSTEM
│   └── README_instalacion.md          # Guía instalación por sucursal
├── systemd/
│   └── hikvision-worker.service       # Servicio systemd
├── sql/
│   └── migraciones.sql                # ALTER + CREATE tablas
├── .github/workflows/
│   └── deploy.yml                     # GitHub Actions deploy
├── .env.example
├── requirements.txt
└── README.md
```

---

## Sucursales configuradas

| Sucursal      | cod | Puerto VPS | Canal | Túnel activo |
|---------------|-----|------------|-------|--------------|
| Granada       | 10  | 9554       | 101   | ✅            |
| Las Brisas    | 16  | 9561       | 101   | ✅            |
| Masaya        | —   | 9555       | 101   | ⏳ pendiente  |
| Central       | —   | 9556       | 101   | ⏳ pendiente  |
| Estelí        | —   | 9557       | 101   | ⏳ pendiente  |
| Calli         | —   | 9558       | 101   | ⏳ pendiente  |
| Villa Fontana | —   | 9559       | 101   | ⏳ pendiente  |
| León          | —   | 9560       | 101   | ⏳ pendiente  |

---

## Próxima etapa

- [ ] Activar worker daemon: `systemctl start hikvision-worker`
- [ ] Extender a Las Brisas (puerto 9561 ya reservado)
- [ ] Encolar día completo automáticamente (cron diario a las 23:00 NI)
- [ ] Dashboard en `erp.batidospitaya.com` para ver calificaciones
- [ ] Expandir análisis: limpieza de local, cumplimiento de tiempos
