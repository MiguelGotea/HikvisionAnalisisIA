# dvr_ntp_setup — Activación automática NTP en DVRs Hikvision

Herramienta auxiliar dentro de `HikvisionAnalisisIA` que configura NTP en todos los DVRs Hikvision de la red, apuntando a `time.google.com` con zona horaria `America/Managua (UTC-6)`.

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
    ├── requirements.txt     # requests + python-dotenv
    ├── .env.example         # Plantilla de variables opcionales
    └── logs/
        └── ntp_setup.log    # Rotativo: 5 MB × 3 archivos
```

Y en `systemd/`:
```
dvr-ntp-setup.service   # oneshot que ejecuta el script
dvr-ntp-setup.timer     # dispara a medianoche Nicaragua (06:00 UTC)
```

El endpoint PHP que expone los DVRs desde la BD está en el repo `api.batidospitaya.com`:
```
api/hikvision/dvr_sucursales.php
```

> **Nota — Firmware legacy:** Algunos DVRs más antiguos no soportan el endpoint
> `ISAPI/System/time/NtpServers/1` (devuelven 404 en GET y PUT). El script detecta esto
> automáticamente, aplica el cambio de `timeMode=NTP` vía `ISAPI/System/time` (compatible
> con todos los modelos), y marca el DVR como `SUCCESS`. Estos modelos también pueden
> devolver `timeMode=''` en el GET aunque el cambio se haya aplicado (quirk de firmware).

---

## ¿Qué necesita el .env?

> **No se requiere ningún archivo .env adicional.**

El módulo reutiliza el `.env` principal del proyecto en `/opt/hikvision-ia/.env`, que ya contiene:
- `HIK_API_TOKEN` — token para `api.batidospitaya.com`
- `HIK_API_BASE_URL` — URL base de la API

Las variables específicas de NTP (`NTP_SERVER`, `HIK_TIMEZONE`, `TIMEOUT_SEGUNDOS`, etc.) tienen valores por defecto en `config.py`.

**Solo necesitás un `.env.local`** si querés sobreescribir algún valor (p. ej. webhook):
```bash
cp /opt/hikvision-ia/dvr_ntp_setup/.env.example \
   /opt/hikvision-ia/dvr_ntp_setup/.env.local
nano /opt/hikvision-ia/dvr_ntp_setup/.env.local
```

---

## Instalación completa en el VPS

El código llega automáticamente al VPS vía GitHub Actions en cada push.

### Paso 1 — Verificar dependencias
```bash
/opt/hikvision-ia/venv/bin/pip list | grep -E "requests|python-dotenv"
# Si no aparecen:
/opt/hikvision-ia/venv/bin/pip install -r /opt/hikvision-ia/dvr_ntp_setup/requirements.txt
```

### Paso 2 — Instalar el timer systemd (una sola vez)
```bash
cp /opt/hikvision-ia/systemd/dvr-ntp-setup.service /etc/systemd/system/
cp /opt/hikvision-ia/systemd/dvr-ntp-setup.timer   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dvr-ntp-setup.timer

# Verificar que quedó activo
systemctl list-timers dvr-ntp-setup.timer
```

### Paso 3 — Verificar primer ejecución (dry-run)
```bash
cd /opt/hikvision-ia
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main --dry-run
```

✅ Instalación completa. El timer corre automáticamente desde aquí.

---

## Uso manual

> **Importante:** ejecutar siempre desde `/opt/hikvision-ia/`

```bash
cd /opt/hikvision-ia

# Todos los DVRs activos
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main

# Solo un DVR (por cod_sucursal)
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main --cod-sucursal 2

# Dry-run (ver qué haría sin hacer cambios)
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main --dry-run

# Más workers para ir más rápido
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main --workers 10
```

**Alias opcional para no escribir el path completo:**
```bash
echo "alias dvr-ntp='/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main'" >> ~/.bashrc
source ~/.bashrc
# Uso: dvr-ntp --cod-sucursal 2
```

### Ejecutar el servicio systemd manualmente
```bash
systemctl start dvr-ntp-setup.service
journalctl -u dvr-ntp-setup -f
```

---

## Pruebas manuales de funcionamiento

### Prueba completa — Simular un corte de luz

Esta es la prueba definitiva: desconfigurar un DVR manualmente y dejar que el script lo corrija.

#### Paso 1 — Verificar estado actual del DVR

```bash
# Sustituir 9652 por el puerto HTTP VPS del DVR y las credenciales correctas
curl -s --digest -u admin:CLAVE \
  http://127.0.0.1:9652/ISAPI/System/time | grep -E "timeMode|timeZone"
```

Resultado cuando está bien configurado:
```xml
<timeMode>NTP</timeMode>
<timeZone>CST+6:00:00</timeZone>
```

#### Paso 2 — Desconfigurar (simular corte de luz)

```bash
curl -s --digest -u admin:CLAVE \
  -X PUT http://127.0.0.1:9652/ISAPI/System/time \
  -H "Content-Type: application/xml" \
  -d '<?xml version="1.0" encoding="UTF-8"?>
<Time version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <timeMode>manual</timeMode>
  <timeZone>CST+6:00:00</timeZone>
</Time>'
```

#### Paso 3 — Confirmar que quedó en manual

```bash
curl -s --digest -u admin:CLAVE \
  http://127.0.0.1:9652/ISAPI/System/time | grep timeMode
# Debe mostrar: <timeMode>manual</timeMode>
```

#### Paso 4 — Ejecutar el script para corregirlo

```bash
cd /opt/hikvision-ia
/opt/hikvision-ia/venv/bin/python -m dvr_ntp_setup.main --cod-sucursal 2
```

Salida esperada:
```
[INFO] [León] 192.168.1.20 — timeMode actual: 'manual'. Requiere cambio.
[INFO] [León] 192.168.1.20 — PUT /ISAPI/System/time → 200
[INFO] [León] 192.168.1.20 — PUT /ISAPI/System/time/NtpServers/1 → 200
[INFO] [León] 192.168.1.20 — Verificación OK → SUCCESS
```

#### Paso 5 — Confirmar que quedó corregido

```bash
curl -s --digest -u admin:CLAVE \
  http://127.0.0.1:9652/ISAPI/System/time | grep -E "timeMode|timeZone"
# <timeMode>NTP</timeMode>

curl -s --digest -u admin:CLAVE \
  http://127.0.0.1:9652/ISAPI/System/time/NtpServers/1 | grep hostName
# <hostName>time.google.com</hostName>
```

---

### Verificar estado de cualquier DVR sin ejecutar el script

```bash
# Ver modo de tiempo
curl -s --digest -u USUARIO:CLAVE \
  http://127.0.0.1:PUERTO/ISAPI/System/time

# Ver servidor NTP configurado
curl -s --digest -u USUARIO:CLAVE \
  http://127.0.0.1:PUERTO/ISAPI/System/time/NtpServers/1
```

### Consultar puertos de todas las sucursales

```bash
curl -s \
  -H "X-WSP-Token: $(grep HIK_API_TOKEN /opt/hikvision-ia/.env | cut -d= -f2)" \
  "https://api.batidospitaya.com/api/hikvision/dvr_sucursales.php?tunel_activo=1" \
  | python3 -m json.tool | grep -E "nombre_sucursal|puerto_http_vps|portal_ip_local"
```

---

## Estados por DVR

| Estado | Descripción |
|--------|-------------|
| `SUCCESS` | NTP configurado y verificado correctamente |
| `ALREADY_OK` | Ya tenía NTP con `time.google.com` — sin cambios |
| `UNREACHABLE` | Timeout o error de conexión (sin túnel / DVR apagado) |
| `AUTH_ERROR` | 401 Unauthorized — credenciales incorrectas |
| `PARTIAL` | Error inesperado en algún paso de configuración |
| `FAILED` | Excepción no manejada |

---

## Exit codes

| Código | Significado |
|--------|-------------|
| `0` | Todos los DVRs son SUCCESS o ALREADY_OK |
| `1` | Al menos un DVR falló, UNREACHABLE o AUTH_ERROR |
| `2` | Error fatal (API no disponible, variable faltante) |

---

## Logs

```bash
# Log en archivo (rotativo 5MB × 3)
cat /opt/hikvision-ia/dvr_ntp_setup/logs/ntp_setup.log

# Log via journald (cuando corre como servicio systemd)
journalctl -u dvr-ntp-setup -f
journalctl -u dvr-ntp-setup --since today
```

---

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `HIK_API_TOKEN` | *(del .env principal)* | Token API de `api.batidospitaya.com` |
| `HIK_API_BASE_URL` | *(del .env principal)* | URL base API |
| `NTP_SERVER` | `time.google.com` | Servidor NTP a configurar |
| `NTP_PORT` | `123` | Puerto NTP |
| `NTP_SYNC_INTERVAL` | `60` | Intervalo de sync (minutos) |
| `HIK_TIMEZONE` | `CST+6:00:00` | Timezone Hikvision para UTC-6 Nicaragua |
| `TIMEOUT_SEGUNDOS` | `10` | Timeout HTTP por DVR (segundos) |
| `MAX_WORKERS` | `5` | Workers paralelos |
| `NTP_WEBHOOK_URL` | *(vacío)* | URL del webhook final (opcional) |
| `NTP_WEBHOOK_TOKEN` | *(vacío)* | Bearer token para el webhook (opcional) |

> **Nota sobre timezone Hikvision:** La convención es **invertida**. UTC-6 (Nicaragua) se escribe `CST+6:00:00`.

---

## Acceso a DVRs

El script corre en el **VPS** con acceso a los DVRs vía túnel SSH inverso:

- DVRs con `puerto_http_vps` → `http://127.0.0.1:{puerto}` (túnel local en el VPS)
- DVRs sin `puerto_http_vps` → `http://{portal_ip_local}:80` (IP directa por bridge)
