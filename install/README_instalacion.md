# Guía de Instalación — Túnel SSH DVR por Sucursal

## Arquitectura del sistema

```
PC Sucursal  ─SSH Tunnel─►  VPS (198.211.97.243)  ◄─HTTP─  ERP (Hostinger)
   DVR local                  snapshot_server :8765
                              Puerto RTSP :9554–9590
                              Puerto HTTP :9654–9690  (DVR moderno, ISAPI)
```

El **snapshot_server** detecta automáticamente el tipo de DVR:
- **DVR moderno (ISAPI)** → usa `puerto_http_vps` → imagen **en vivo instantánea**
- **DVR firmware antiguo** → usa `puerto_rtsp_vps` + ffmpeg → imagen de **~5 min atrás** (segmento de grabación)

---

## Sucursales — Puertos configurados

| Sucursal      | cod | Archivo bat                   | RTSP VPS | HTTP VPS | DVR IP            | Tipo        |
|---------------|:---:|-------------------------------|:--------:|:--------:|-------------------|-------------|
| Leon          | 2   | `tunel_dvr_leon.bat`          | 9552     | —        | 192.168.1.20      | RTSP only   |
| Matagalpa     | 4   | `tunel_dvr_matagalpa.bat`     | 9574     | —        | 192.168.1.40      | RTSP only   |
| Esteli        | 5   | `tunel_dvr_esteli.bat`        | 9575     | —        | 192.168.1.50      | RTSP only   |
| Altamira      | 7   | `tunel_dvr_altamira.bat`      | 9577     | —        | 192.168.1.70      | RTSP only   |
| Villa Fontana | 9   | `tunel_dvr_villafontana.bat`  | 9579     | —        | 192.168.1.90      | RTSP only   |
| Granada       | 10  | `tunel_dvr_granada.bat`       | 9554     | 9654     | 192.168.1.100     | **ISAPI** ✅ |
| Las Colinas   | 11  | `tunel_dvr_lascolinas.bat`    | 9581     | —        | 192.168.1.110     | RTSP only   |
| Masaya        | 12  | `tunel_dvr_masaya.bat`        | 9582     | —        | 192.168.1.120     | RTSP only   |
| Natura        | 13  | `tunel_dvr_natura.bat`        | 9583     | —        | 192.168.1.130     | RTSP only   |
| Las Brisas    | 16  | `tunel_dvr_lasbrisas.bat`     | 9561     | —        | 192.168.0.160     | RTSP only   |
| Rivas         | 17  | `tunel_dvr_rivas.bat`         | 9587     | —        | 192.168.40.170    | RTSP only   |
| Oficinas      | 18  | `tunel_dvr_oficinas.bat`      | 9588     | —        | 192.168.0.200     | RTSP only   |

> **Convención de puertos:** HTTP = RTSP + 100 (ej: RTSP 9554 → HTTP 9654)

### Verificar si un DVR soporta ISAPI

Desde la PC de la sucursal, abrir en el navegador:
```
http://admin:CLAVE@192.168.1.X:80/ISAPI/Streaming/channels/101/picture
```
- Si abre una imagen → soporta ISAPI → agregar `puerto_http_vps` en la BD y tunel HTTP en el `.bat`
- Si da error → solo RTSP → dejar `puerto_http_vps` en NULL

---

## Paso 1 — Generar llave SSH (si es una PC nueva)

```powershell
# En la PC de la sucursal (PowerShell)
ssh-keygen -t ed25519 -C "sucursal_nombre"
# Presiona Enter a todo, sin contraseña

# Copiar la llave pública (empieza con "ssh-ed25519 ...")
cat $HOME\.ssh\id_ed25519.pub
```

---

## Paso 2 — Autorizar la llave en el VPS

```bash
# En el VPS (pegar la llave copiada del paso anterior):
echo "ssh-ed25519 AAAA... sucursal_nombre" >> ~/.ssh/authorized_keys
```

---

## Paso 3 — Probar conectividad SSH manualmente

Desde la PC de la sucursal, probar que conecta sin contraseña (queda parpadeando = OK):

```cmd
# Solo RTSP (DVR firmware antiguo)
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 ^
    -R 0.0.0.0:PUERTO_RTSP:DVR_IP:554 root@198.211.97.243 -N

# RTSP + HTTP (DVR moderno con ISAPI)
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 ^
    -R 0.0.0.0:PUERTO_RTSP:DVR_IP:554 ^
    -R 0.0.0.0:PUERTO_HTTP:DVR_IP:80 root@198.211.97.243 -N
```

Verificar en el VPS que el puerto escucha:
```bash
ss -tlnp | grep PUERTO_RTSP
# Debe mostrar: LISTEN 0  128  0.0.0.0:PUERTO ...
```

`Ctrl+C` para salir cuando termines de probar.

---

## Paso 4 — Copiar el archivo .bat a C:\

```powershell
Copy-Item "C:\Users\Pitaya\Google Drive BP\...\tunel_dvr_SUCURSAL.bat" "C:\tunel_dvr_SUCURSAL.bat"
```

---

## Paso 5 — Instalar tarea programada (como Administrador)

```powershell
powershell.exe -ExecutionPolicy Bypass `
  -File "C:\users\pitaya\Google Drive BP\Sistema Ultima Version\Llaves WireGuard\setup_tarea_programada.ps1" `
  -BatPath "C:\tunel_dvr_SUCURSAL.bat" `
  -NombreTarea "TunelDVR_SUCURSAL"
```

El script automáticamente:
- Copia la llave SSH al perfil SYSTEM (`C:\Windows\System32\config\systemprofile\.ssh\`)
- Copia el known_hosts para evitar prompts interactivos
- Crea la tarea programada que arranca con Windows como cuenta `SYSTEM`
- Pregunta si iniciar el túnel inmediatamente

---

## Paso 6 — Verificar desde el VPS

```bash
# Ver puertos de la sucursal
ss -tlnp | grep 9579

# Ver todos los túneles activos
ss -tlnp | grep -E "955[0-9]|956[0-9]|957[0-9]|958[0-9]"

# Probar DVR (RTSP) — reemplaza puerto y clave
ffmpeg -rtsp_transport tcp \
  -i "rtsp://admin:CLAVE@127.0.0.1:PUERTO_RTSP/PSIA/Streaming/tracks/101" \
  -frames:v 1 /tmp/test_tunel.jpg -y && file /tmp/test_tunel.jpg

# Probar DVR moderno (ISAPI HTTP)
curl --digest --user admin:CLAVE \
  http://127.0.0.1:PUERTO_HTTP/ISAPI/Streaming/channels/101/picture \
  -o /tmp/test_isapi.jpg && file /tmp/test_isapi.jpg
```

---

## Agregar nueva sucursal

### 1. Base de datos

```sql
-- DVR firmware antiguo (solo RTSP)
UPDATE DVR_Sucursales
SET puerto_rtsp_vps = 9579,
    canal_caja      = 101,
    tunel_activo    = 1,
    puerto_http_vps = NULL      -- sin ISAPI
WHERE cod_sucursal = 9;

-- DVR moderno (ISAPI + RTSP)
UPDATE DVR_Sucursales
SET puerto_rtsp_vps = 9554,
    puerto_http_vps = 9654,     -- HTTP = RTSP + 100
    canal_caja      = 101,
    tunel_activo    = 1
WHERE cod_sucursal = 10;
```

### 2. Firewall VPS

```bash
ufw allow PUERTO_RTSP/tcp
ufw allow PUERTO_HTTP/tcp   # Solo si el DVR soporta ISAPI
```

### 3. Archivo .bat

- **Solo RTSP** → copiar cualquier `.bat` existente como Villa Fontana (sin línea HTTP)
- **ISAPI + RTSP** → copiar `tunel_dvr_granada.bat` y ajustar IPs y puertos

---

## Comandos útiles — Windows (PowerShell)

```powershell
# Ver estado de la tarea
Get-ScheduledTask -TaskName "TunelDVR_VillaFontana"

# Iniciar manualmente
Start-ScheduledTask -TaskName "TunelDVR_VillaFontana"

# Detener
Stop-ScheduledTask -TaskName "TunelDVR_VillaFontana"

# Reiniciar (aplica nuevo .bat)
Stop-ScheduledTask  -TaskName "TunelDVR_VillaFontana"
Start-ScheduledTask -TaskName "TunelDVR_VillaFontana"
```

---

## Comandos útiles — VPS

```bash
# Logs del snapshot server
journalctl -u hikvision-snapshot -n 30 --no-pager

# Logs del worker de análisis IA
journalctl -u hikvision-worker -f

# Reiniciar snapshot server
systemctl restart hikvision-snapshot

# Estado de servicios
systemctl status hikvision-snapshot hikvision-worker

# Ver todos los túneles activos
ss -tlnp | grep -E "955[0-9]|956[0-9]|957[0-9]|958[0-9]"
```
