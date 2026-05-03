# HikvisionAnalisisIA

Sistema automatizado de análisis de atención al cliente mediante cámaras DVR HiLook/Hikvision e Inteligencia Artificial (Gemini).

---

## Arquitectura

```
api.batidospitaya.com (Hostinger)          VPS DigitalOcean (198.211.97.243)
──────────────────────────────────         ────────────────────────────────────
api/hikvision/                             /opt/hikvision-ia/
  ├── encolar_pedido.php   ◄── POST        src/
  ├── encolar_dia_completo.php ◄── POST      ├── worker.py      (daemon loop)
  ├── pedidos_cola.php     ──► GET           ├── downloader.py  (RTSP/ffmpeg)
  ├── marcar_estado.php    ◄── POST          ├── preprocessor.py(compresión)
  ├── registrar_resultado.php ◄── POST       └── analyzer.py    (Gemini IA)
  ├── reprocesar_pedido.php◄── POST
  └── gemini_key.php       ──► GET

BD u839374897_erp (Hostinger)              Túneles SSH inversos (por sucursal)
  ├── VentasGlobalesAccessCSV              PC Sucursal → VPS:9554 → DVR:554
  ├── DVR_Sucursales                       (Granada activo, otros en expansión)
  ├── sucursales
  ├── hikvision_cola_analisis   (queue)
  └── hikvision_analisis_ia_atencion (resultados)
```

---

## Flujo de procesamiento

```
1. Encolar pedido (manual o automático)
        │
        ▼
2. worker.py: poll pedidos_cola.php cada 30s
        │
        ▼
3. downloader.py: descarga clip vía RTSP (túnel SSH)
   rtsp://admin:CLAVE@198.211.97.243:9554/PSIA/Streaming/tracks/101
   ?starttime=20260502T140000Z&endtime=20260502T140500Z
        │
        ▼
4. preprocessor.py: comprimir con ffmpeg
   480p | 5fps | 300kbps → ~6MB para 3 min
        │
        ▼
5. analyzer.py: subir a Gemini Files API → analizar
   Califica: amabilidad, saludo, despedida, oferta_membresía (1-10)
        │
        ▼
6. registrar_resultado.php → guardar en hikvision_analisis_ia_atencion
        │
        ▼
7. Borrar videos temporales del VPS
```

---

## Deploy

```bash
# Primer setup (solo una vez via SSH):
ssh root@198.211.97.243
cd /opt/hikvision-ia
bash scripts/setup_vps.sh

# Después: solo push a main
git push origin main
# GitHub Actions hace rsync + systemctl restart hikvision-worker
```

### Secrets GitHub requeridos

| Secret       | Valor                              |
|--------------|------------------------------------|
| `DO_SSH_KEY` | Llave privada SSH (`id_ed25519`)   |
| `DO_HOST`    | `198.211.97.243`                   |
| `DO_USER`    | `root`                             |
| `DO_PATH`    | `/opt/hikvision-ia`                |

---

## Comandos del VPS

```bash
# Estado del worker
systemctl status hikvision-worker

# Logs en tiempo real
journalctl -u hikvision-worker -f

# Reiniciar
systemctl restart hikvision-worker

# Test manual de un pedido específico
cd /opt/hikvision-ia
venv/bin/python scripts/test_manual.py --pedido 12345 --local 10

# Solo descargar (sin analizar, para depuración)
venv/bin/python scripts/test_manual.py --pedido 12345 --local 10 --solo-descargar
```

---

## Herramientas API (desde cualquier cliente con el token)

### Encolar pedido puntual (manual)
```http
POST https://api.batidospitaya.com/api/hikvision/encolar_pedido.php
X-WSP-Token: <token>
Content-Type: application/json

{ "cod_pedido": 12345, "local": "10" }
```

### Encolar día completo (automático, sin delivery)
```http
POST https://api.batidospitaya.com/api/hikvision/encolar_dia_completo.php
X-WSP-Token: <token>
Content-Type: application/json

{ "fecha": "2026-05-02", "local": "10" }
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

## Estructura del proyecto

```
hikvisionanalisisia/
├── src/
│   ├── __init__.py
│   ├── config.py          # Variables de entorno centralizadas
│   ├── logger.py          # Logger para journald
│   ├── api_client.py      # HTTP client → api.batidospitaya.com
│   ├── downloader.py      # Descarga RTSP via ffmpeg
│   ├── preprocessor.py    # Compresión ffmpeg (480p/5fps/300kbps)
│   ├── analyzer.py        # Análisis Gemini (Files API)
│   └── worker.py          # Daemon principal (ThreadPoolExecutor)
├── scripts/
│   ├── setup_vps.sh       # Setup inicial VPS (ejecutar 1 vez)
│   └── test_manual.py     # CLI para test de pedido específico
├── install/
│   ├── tunel_dvr_granada.bat          # Script túnel SSH Granada
│   ├── setup_tarea_programada.ps1     # Crea tarea programada Windows
│   └── README_instalacion.md          # Guía instalación por sucursal
├── systemd/
│   └── hikvision-worker.service       # Servicio systemd
├── sql/
│   └── migraciones.sql                # SQL: nuevas tablas y columnas
├── .github/workflows/
│   └── deploy.yml                     # GitHub Actions deploy
├── .env.example                       # Template de configuración
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Sucursales configuradas

| Sucursal      | cod | Puerto VPS | Canal | Túnel activo |
|---------------|-----|------------|-------|--------------|
| Granada       | 10  | 9554       | 101   | ✅           |
| Masaya        | —   | 9555       | 101   | ⏳ pendiente |
| Central       | —   | 9556       | 101   | ⏳ pendiente |
| Estelí        | —   | 9557       | 101   | ⏳ pendiente |
| Calli         | —   | 9558       | 101   | ⏳ pendiente |
| Villa Fontana | —   | 9559       | 101   | ⏳ pendiente |
| León          | —   | 9560       | 101   | ⏳ pendiente |
| Las Brisas    | 16  | 9561       | 101   | ✅           |

---

## Próxima etapa

- [ ] Dashboard en `erp.batidospitaya.com` para visualizar análisis
- [ ] Ampliar a análisis de limpieza y cumplimiento de tiempos
- [ ] Automatizar encolar_dia_completo con cron/timer systemd
