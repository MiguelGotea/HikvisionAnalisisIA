# Guia de Instalacion — Tunel SSH DVR por Sucursal

## Requisitos previos (en cada PC de sucursal)

- Windows 10/11 con OpenSSH instalado
- La llave SSH `id_ed25519` registrada en el VPS (`~/.ssh/authorized_keys`)
- Acceso a Internet y al DVR local

---

## Sucursales — Puertos y archivos

| Sucursal      | cod_sucursal | Archivo bat                   | Puerto VPS | DVR IP local      |
|---------------|:------------:|-------------------------------|:----------:|-------------------|
| Leon          | 2            | `tunel_dvr_leon.bat`          | 9552       | 192.168.1.20      |
| Matagalpa     | 4            | `tunel_dvr_matagalpa.bat`     | 9574       | 192.168.1.40      |
| Esteli        | 5            | `tunel_dvr_esteli.bat`        | 9575       | 192.168.1.50      |
| Altamira      | 7            | `tunel_dvr_altamira.bat`      | 9577       | 192.168.1.70      |
| Villa Fontana | 9            | `tunel_dvr_villafontana.bat`  | 9579       | 192.168.1.90      |
| Granada       | 10           | `tunel_dvr_granada.bat`       | 9554       | 192.168.1.100     |
| Las Colinas   | 11           | `tunel_dvr_lascolinas.bat`    | 9581       | 192.168.1.110     |
| Masaya        | 12           | `tunel_dvr_masaya.bat`        | 9582       | 192.168.1.120     |
| Natura        | 13           | `tunel_dvr_natura.bat`        | 9583       | 192.168.1.130     |
| Las Brisas    | 16           | `tunel_dvr_lasbrisas.bat`     | 9561       | 192.168.0.160     |
| Rivas         | 17           | `tunel_dvr_rivas.bat`         | 9587       | 192.168.40.170    |
| Oficinas      | 18           | `tunel_dvr_oficinas.bat`      | 9588       | 192.168.0.200     |

---

## Paso 1 — Generar llave SSH (si no existe)

Si la PC es nueva, genera una llave y autorizala en el VPS:

1. **Generar la llave** (presiona Enter a todo, sin contrasena):
   ```powershell
   ssh-keygen -t ed25519 -C "sucursal_nombre"
   ```

2. **Copiar la llave publica**:
   ```powershell
   cat $HOME\.ssh\id_ed25519.pub
   # Copia el texto que empieza con "ssh-ed25519 ..."
   ```

---

## Paso 2 — Registrar llave SSH en el VPS

Accede al VPS desde una PC que ya tenga acceso y pega la llave:

```bash
# En el VPS:
echo "pega_aqui_la_llave_copiada" >> ~/.ssh/authorized_keys
```

---

## Paso 3 — Probar conectividad SSH manualmente

La llave debe estar en `C:\Users\Pitaya\.ssh\id_ed25519` (o el usuario que corresponda).

Probar que conecta sin pedir contrasena (queda parpadeando = OK):

```cmd
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 0.0.0.0:PUERTO:DVR_IP:554 root@198.211.97.243 -N
```

Ejemplo para Villa Fontana:
```cmd
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 0.0.0.0:9579:192.168.1.90:554 root@198.211.97.243 -N
```

Mientras parpadea, verificar en el VPS que el puerto esta escuchando:
```bash
ss -tlnp | grep 9579
# Debe mostrar: LISTEN 0  128  0.0.0.0:9579 ...
```

`Ctrl+C` para salir cuando termines de probar.

---

## Paso 4 — Copiar el script bat a C:\

Copiar el archivo `.bat` correspondiente a la sucursal a `C:\`:

```powershell
# Ejemplo: copiar desde Google Drive al disco C
Copy-Item "C:\Users\Pitaya\Google Drive BP\Sistema Ultima Version\Llaves WireGuard\tunel_dvr_lascolinas.bat" "C:\tunel_dvr_lascolinas.bat"
```

---

## Paso 5 — Instalar la tarea programada (como Administrador)

Abrir **PowerShell como Administrador** y ejecutar:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "C:\users\pitaya\Google Drive BP\Sistema Ultima Version\Llaves WireGuard\setup_tarea_programada.ps1" -BatPath "C:\tunel_dvr_lascolinas.bat" -NombreTarea "TunelDVR_Lascolinas"
```

> **Ajusta** `-BatPath` y `-NombreTarea` segun la sucursal. Ejemplos:
> - `-BatPath "C:\tunel_dvr_granada.bat" -NombreTarea "TunelDVR_Granada"`
> - `-BatPath "C:\tunel_dvr_leon.bat" -NombreTarea "TunelDVR_Leon"`

El script automaticamente:
- Copia la llave SSH al perfil SYSTEM (`C:\Windows\System32\config\systemprofile\.ssh\`)
- Copia el known_hosts para evitar prompts interactivos
- Crea la tarea programada que arranca con Windows
- Pregunta si iniciar el tunel inmediatamente

La tarea:
- Se ejecuta como `SYSTEM` (no necesita usuario conectado)
- Arranca automaticamente con Windows
- Se reconecta si el tunel cae (loop cada 10 segundos)

---

## Paso 6 — Verificar el tunel desde el VPS

Desde el VPS, verificar que el puerto esta escuchando:

```bash
# Ver tunel especifico (ejemplo Villa Fontana)
ss -tlnp | grep 9579

# Ver todos los tuneles activos
ss -tlnp | grep -E "955[0-9]|957[0-9]|958[0-9]"
```

Probar que el DVR responde a traves del tunel:
```bash
ffmpeg -rtsp_transport tcp -i "rtsp://admin:Nihonk03@127.0.0.1:9581/PSIA/Streaming/tracks/101" -t 5 -f null - 2>&1 | tail -5
```

---

## Para agregar una nueva sucursal

1. Instalar llave SSH en la nueva PC
2. Copiar el `.bat` con el puerto correcto a `C:\`
3. Ejecutar `setup_tarea_programada.ps1` como Administrador
4. En la BD, actualizar `DVR_Sucursales`:
   ```sql
   UPDATE DVR_Sucursales
   SET puerto_rtsp_vps = 9579,
       canal_caja      = 101,
       tunel_activo    = 1
   WHERE cod_sucursal = 9;
   ```
5. Abrir el puerto en el firewall del VPS:
   ```bash
   ufw allow 9579/tcp
   ```

---

## Comandos utiles en Windows (PowerShell)

```powershell
# Ver estado de la tarea (reemplaza el nombre segun sucursal)
Get-ScheduledTask -TaskName "TunelDVR_VillaFontana"

# Iniciar manualmente
Start-ScheduledTask -TaskName "TunelDVR_VillaFontana"

# Detener
Stop-ScheduledTask -TaskName "TunelDVR_VillaFontana"

# Ver historial de ejecuciones
Get-ScheduledTaskInfo -TaskName "TunelDVR_VillaFontana"

# Prueba manual del tunel (queda parpadeando mientras esta activo)
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 0.0.0.0:9579:192.168.1.90:554 root@198.211.97.243 -N
```

---

## Comandos utiles en el VPS

```bash
# Ver logs del worker
journalctl -u hikvision-worker -f

# Reiniciar el worker
systemctl restart hikvision-worker

# Ver todos los puertos de tuneles activos
ss -tlnp | grep -E "955[0-9]|957[0-9]|958[0-9]"

# Estado del servicio
systemctl status hikvision-worker
```
