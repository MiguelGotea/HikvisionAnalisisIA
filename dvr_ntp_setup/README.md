# dvr_ntp_setup — Activación automática NTP en DVRs Hikvision

Herramienta auxiliar dentro de `HikvisionAnalisisIA` que configura el protocolo NTP en todos los DVRs Hikvision de la red, apuntando a `time.google.com` con zona horaria `America/Managua (UTC-6)`.

---

## Estructura del módulo

```
HikvisionAnalisisIA/
└── dvr_ntp_setup/
    ├── __init__.py          # Paquete Python
    ├── config.py            # Variables de entorno
    ├── db.py                # Consulta DVRs vía API REST
    ├── hikvision.py         # Cliente ISAPI (GET/PUT tiempo y NTP)
    ├── logger.py            # Logging consola + archivo rotativo
    ├── main.py              # Entry point y orquestador
    ├── notifier.py          # Webhook de resumen al finalizar
    ├── test_hikvision.py    # Tests unitarios (sin red real)
    ├── requirements.txt     # Solo: requests + python-dotenv
    ├── .env.example         # Plantilla de variables locales
    └── logs/
        └── ntp_setup.log    # Rotativo: 5 MB × 3 archivos
```

Y en `systemd/`:
```
dvr-ntp-setup.service   # oneshot que ejecuta el script
dvr-ntp-setup.timer     # dispara a medianoche Nicaragua (06:00 UTC)
```

---

## Instalación en el VPS

### 1. Asegurarse que el venv principal ya tenga las dependencias

El módulo usa solo `requests` y `python-dotenv`, que ya están instaladas en el proyecto principal. Para confirmar:

```bash
/opt/hikvision-ia/venv/bin/pip list | grep -E "requests|python-dotenv"
```

Si no están, instalar dentro del venv existente:

```bash
/opt/hikvision-ia/venv/bin/pip install -r /opt/hikvision-ia/dvr_ntp_setup/requirements.txt
```

### 2. Crear archivo de configuración local (opcional)

Solo si querés sobreescribir valores del `.env` principal:

```bash
cp /opt/hikvision-ia/dvr_ntp_setup/.env.example \
   /opt/hikvision-ia/dvr_ntp_setup/.env.local

# Editar los valores que necesitás (webhook, timeouts, etc.)
nano /opt/hikvision-ia/dvr_ntp_setup/.env.local
```

### 3. Instalar el servicio y timer systemd

```bash
# Copiar unidades
cp /opt/hikvision-ia/systemd/dvr-ntp-setup.service /etc/systemd/system/
cp /opt/hikvision-ia/systemd/dvr-ntp-setup.timer   /etc/systemd/system/

# Recargar systemd
systemctl daemon-reload

# Activar el timer (se ejecutará automáticamente cada día)
systemctl enable --now dvr-ntp-setup.timer

# Verificar que el timer está activo
systemctl list-timers dvr-ntp-setup.timer
```

### 4. Instalar el endpoint de API en el servidor

Copiar el archivo `dvr_sucursales.php` al servidor Hostinger:

```
api.batidospitaya.com/api/hikvision/dvr_sucursales.php
```

---

## Uso manual

```bash
cd /opt/hikvision-ia

# Todos los DVRs activos (5 workers paralelos por defecto)
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main

# Solo un DVR específico por código de sucursal
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main --cod-sucursal 2

# Simular sin hacer cambios (dry-run)
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main --dry-run

# Con más workers para acelerar (máx recomendado: 10)
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main --workers 10
```

### Ejecutar manualmente el servicio systemd

```bash
systemctl start dvr-ntp-setup.service
journalctl -u dvr-ntp-setup -f   # ver logs en tiempo real
```

---

## Exit codes

| Código | Significado |
|--------|-------------|
| `0`    | Todos los DVRs son SUCCESS o ALREADY_OK |
| `1`    | Al menos un DVR falló, fue UNREACHABLE o tuvo AUTH_ERROR |
| `2`    | Error fatal (BD no disponible, variable de entorno faltante) |

---

## Estados por DVR

| Estado | Descripción |
|--------|-------------|
| `SUCCESS` | NTP configurado y verificado correctamente |
| `ALREADY_OK` | Ya tenía NTP con `time.google.com` — sin cambios |
| `UNREACHABLE` | Timeout o error de conexión (sin red / DVR apagado) |
| `AUTH_ERROR` | 401 Unauthorized — credenciales incorrectas |
| `PARTIAL` | Algunos pasos OK pero verificación final discrepante |
| `FAILED` | Error inesperado durante el proceso |

---

## Tests unitarios

No requieren red ni DVRs reales — todo está mockeado:

```bash
cd /opt/hikvision-ia
/opt/hikvision-ia/venv/bin/python -m pytest dvr_ntp_setup/test_hikvision.py -v
```

Cobertura de los tests:
- Parseo XML de `GET /ISAPI/System/time`
- Parseo XML de `GET /ISAPI/System/time/NtpServers/1`
- Lógica `is_already_ok` con 4 combinaciones
- `_procesar_dvr`: ALREADY_OK, SUCCESS, UNREACHABLE, AUTH_ERROR, PARTIAL, dry-run

---

## Logs

```
/opt/hikvision-ia/dvr_ntp_setup/logs/ntp_setup.log
```

- Rotación automática: máx 5 MB por archivo, 3 backups
- También disponibles en journald: `journalctl -u dvr-ntp-setup`

---

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `HIK_API_TOKEN` | *(requerida)* | Token API de `api.batidospitaya.com` |
| `HIK_API_BASE_URL` | `https://api.batidospitaya.com/api/hikvision` | URL base API |
| `NTP_SERVER` | `time.google.com` | Servidor NTP a configurar |
| `NTP_PORT` | `123` | Puerto NTP |
| `NTP_SYNC_INTERVAL` | `60` | Intervalo de sincronización (minutos) |
| `HIK_TIMEZONE` | `CST+6:00:00` | Timezone Hikvision para UTC-6 Nicaragua |
| `TIMEOUT_SEGUNDOS` | `10` | Timeout HTTP por DVR (segundos) |
| `MAX_WORKERS` | `5` | Workers paralelos |
| `NTP_WEBHOOK_URL` | *(vacío)* | URL del webhook final (opcional) |
| `NTP_WEBHOOK_TOKEN` | *(vacío)* | Bearer token para el webhook (opcional) |

> **Nota sobre timezone Hikvision**: La convención es **invertida**. UTC-6 (Nicaragua) se escribe `CST+6:00:00` — el signo es opuesto al estándar POSIX.

---

## Acceso a DVRs

El script corre en el **VPS** que ya tiene rutas directas a las IPs privadas `192.168.x.x` de los DVRs a través del túnel SSH inverso establecido por las PCs locales. No se requiere ninguna configuración de red adicional.

Si el DVR tiene `puerto_http_vps` definido (> 0), el script usa ese puerto en lugar de la IP local directa. Si no, accede directamente a `http://{portal_ip_local}:80`.
