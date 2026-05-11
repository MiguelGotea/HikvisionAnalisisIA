# Guía de Instalación — Túnel SSH DVR por Sucursal

## Requisitos previos (en cada PC de sucursal)

- Windows 10/11 con OpenSSH instalado
- La llave SSH `id_ed25519` registrada en el VPS (`~/.ssh/authorized_keys`)
- Acceso a Internet y al DVR local

---

## Paso 1 — Generar llave SSH (si no existe)

Si la PC es nueva, debes generar una llave y autorizarla en el VPS:

1. **Generar la llave** (presiona Enter a todo, sin contraseña):
   ```powershell
   ssh-keygen -t ed25519 -C "sucursal_nombre"
   ```

2. **Copiar la llave pública**:
   ```powershell
   cat $HOME\.ssh\id_ed25519.pub
   # Copia el texto que empieza con "ssh-ed25519 ..."
   ```

## Paso 2 — Registrar llave SSH 

1. **Registrar en el VPS**:
   Accede al VPS desde una PC que ya tenga acceso y pega la llave:
   ```bash
   # En el VPS:
   echo "pega_aqui_la_llave_copiada" >> ~/.ssh/authorized_keys
   ```

---

## Paso 3 — Verificar la llave SSH

La llave debe estar en `C:\Users\Pitaya\.ssh\id_ed25519` (o el usuario que corresponda).

Probar conectividad:
```cmd
ssh root@198.211.97.243 -N -o StrictHostKeyChecking=no
```
Si conecta sin pedir contraseña, la llave está bien. `Ctrl+C` para salir.

---

## Paso 3 — Copiar el script de túnel

Copiar el archivo `.bat` correspondiente a la sucursal a `C:\`:

| Sucursal      | Archivo                     | Puerto VPS |
|---------------|-----------------------------|------------|
| Granada       | `tunel_dvr_granada.bat`     | 9554       |
| Masaya        | `tunel_dvr_masaya.bat`      | 9555       |
| Central       | `tunel_dvr_central.bat`     | 9556       |
| Estelí        | `tunel_dvr_esteli.bat`      | 9557       |
| Calli         | `tunel_dvr_calli.bat`       | 9558       |
| Villa Fontana | `tunel_dvr_villafontana.bat`| 9559       |
| León          | `tunel_dvr_leon.bat`        | 9560       |
| Las Brisas    | `tunel_dvr_lasbrisas.bat`    | 9561       |

---

## Paso 4 — Crear la tarea programada (como Administrador)

Abrir **PowerShell como Administrador** y ejecutar:

```powershell
# Ajustar la ruta del .bat y el nombre de la tarea según la sucursal
.\setup_tarea_programada.ps1 -BatPath "C:\tunel_dvr_granada.bat" -NombreTarea "TunelDVR_Granada"

powershell.exe -ExecutionPolicy Bypass -File "C:\users\pitaya\Google Drive BP\Sistema Ultima Version\Llaves WireGuard\setup_tarea_programada.ps1" -BatPath "C:\tunel_dvr_villafontana.bat" -NombreTarea "TunelDVR_VillaFontana"
```

Esto crea una tarea que:
- ✅ Se ejecuta como `SYSTEM` (no necesita usuario conectado)
- ✅ Arranca automáticamente con Windows
- ✅ Se reconecta si el túnel cae

> [!IMPORTANT]
> **Nota sobre el usuario SYSTEM**: La tarea programada corre como `SYSTEM`. Para que SSH encuentre la llave, copia la carpeta `.ssh` de tu usuario a:
> `C:\Windows\System32\config\systemprofile\`
> (Debe quedar `C:\Windows\System32\config\systemprofile\.ssh\id_ed25519`)

---

## Paso 5 — Verificar el túnel desde el VPS

Desde el VPS, verificar que el puerto está escuchando:

```bash
ss -tlnp | grep 9554
# Debe mostrar: LISTEN 0 128 0.0.0.0:9554 ...

# Probar conexión RTSP (sin video, solo ver si responde)
ffmpeg -rtsp_transport tcp -i "rtsp://admin:CLAVE@127.0.0.1:9554/PSIA/Streaming/tracks/101" -t 5 -f null - 2>&1 | tail -5
```

---

## Para agregar una nueva sucursal

1. Instalar llave SSH en la nueva PC
2. Copiar el `.bat` con el puerto correcto
3. Crear la tarea programada
4. En la BD, actualizar `DVR_Sucursales`:
   ```sql
   UPDATE DVR_Sucursales
   SET puerto_rtsp_vps = 9555,
       canal_caja      = 101,
       tunel_activo    = 1
   WHERE cod_sucursal = <codigo>;
   ```
5. Abrir el puerto en el firewall del VPS:
   ```bash
   ufw allow 9555/tcp
   ```

---

## Comandos útiles en Windows (PowerShell)

```powershell
# Ver estado de la tarea
Get-ScheduledTask -TaskName "TunelDVR_Granada"

# Iniciar manualmente
Start-ScheduledTask -TaskName "TunelDVR_Granada"

# Detener
Stop-ScheduledTask -TaskName "TunelDVR_Granada"

# Ver historial de ejecuciones
Get-ScheduledTaskInfo -TaskName "TunelDVR_Granada"
```

## Comandos útiles en el VPS

```bash
# Ver logs del worker
journalctl -u hikvision-worker -f

# Reiniciar el worker
systemctl restart hikvision-worker

# Ver puertos de túneles activos
ss -tlnp | grep -E "955[0-9]"

# Estado del servicio
systemctl status hikvision-worker
```
