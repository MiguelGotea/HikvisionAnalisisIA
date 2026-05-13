# ============================================================
# setup_tarea_programada.ps1 -- Crea tarea de Windows para el tunel SSH
# Ejecutar como ADMINISTRADOR en PowerShell
#
# Uso:
#   .\setup_tarea_programada.ps1 -BatPath "C:\tunel_dvr_villafontana.bat" -NombreTarea "TunelDVR_Villafontana"
# ============================================================

param(
    [string]$BatPath    = "C:\tunel_dvr_villafontana.bat",
    [string]$NombreTarea = "TunelDVR_Villafontana"
)

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Configurando tarea programada: $NombreTarea"     -ForegroundColor Cyan
Write-Host "  Archivo: $BatPath"                               -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Verificar que el .bat existe
if (-not (Test-Path $BatPath)) {
    Write-Host "ERROR: No se encontro el archivo $BatPath" -ForegroundColor Red
    Write-Host "Copia el archivo .bat a esa ruta primero." -ForegroundColor Yellow
    exit 1
}

# ============================================================
# PASO CRITICO: Copiar llave SSH al perfil SYSTEM
# La tarea corre como SYSTEM, que no puede leer C:\Users\..\ssh\
# La llave debe estar en C:\Windows\System32\config\systemprofile\.ssh\
# ============================================================
$systemSshDir = "C:\Windows\System32\config\systemprofile\.ssh"
$usuarioActual = $env:USERPROFILE
$llaveFuente   = "$usuarioActual\.ssh\id_ed25519"
$llaveDestino  = "$systemSshDir\id_ed25519"

Write-Host ""
Write-Host "--- Configurando llave SSH para usuario SYSTEM ---" -ForegroundColor Cyan

if (-not (Test-Path $llaveFuente)) {
    Write-Host "ADVERTENCIA: No se encontro la llave en $llaveFuente" -ForegroundColor Yellow
    Write-Host "  Asegurate de haber generado la llave SSH (ssh-keygen -t ed25519)" -ForegroundColor Yellow
} else {
    # Crear directorio si no existe
    if (-not (Test-Path $systemSshDir)) {
        New-Item -ItemType Directory -Force -Path $systemSshDir | Out-Null
        Write-Host "  [OK] Directorio .ssh de SYSTEM creado." -ForegroundColor Gray
    }

    # Copiar llave privada
    Copy-Item -Force $llaveFuente $llaveDestino
    Write-Host "  [OK] Llave privada copiada a perfil SYSTEM" -ForegroundColor Green

    # Copiar known_hosts si existe (evita el prompt interactivo de confirmacion)
    $knownSrc = "$usuarioActual\.ssh\known_hosts"
    $knownDst = "$systemSshDir\known_hosts"
    if (Test-Path $knownSrc) {
        Copy-Item -Force $knownSrc $knownDst
        Write-Host "  [OK] known_hosts copiado" -ForegroundColor Green
    } else {
        # Crear known_hosts vacio para evitar error de permisos
        New-Item -ItemType File -Force -Path $knownDst | Out-Null
        Write-Host "  [INFO] known_hosts creado vacio (se llenara en primera conexion)" -ForegroundColor Gray
    }
}
Write-Host ""

# Eliminar tarea si ya existe (para actualizar)
$tareaExistente = Get-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue
if ($tareaExistente) {
    Write-Host "Eliminando tarea existente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $NombreTarea -Confirm:$false
}

# Definir la accion: ejecutar el .bat
$accion = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatPath`""

# Disparador: Al iniciar el sistema (antes de que el usuario inicie sesion)
$disparador = New-ScheduledTaskTrigger -AtStartup

# Configuracion: ejecutar con privilegios altos, aunque el usuario no este conectado
$config = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 10 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Principal: correr como SYSTEM para no depender de login de usuario
$principal = New-ScheduledTaskPrincipal `
    -UserId "NT AUTHORITY\SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Registrar la tarea
Register-ScheduledTask `
    -TaskName $NombreTarea `
    -Action $accion `
    -Trigger $disparador `
    -Settings $config `
    -Principal $principal `
    -Description "Tunel SSH inverso permanente para DVR de sucursal. Proyecto HikvisionAnalisisIA." `
    -Force

Write-Host ""
Write-Host "[OK] Tarea '$NombreTarea' creada correctamente." -ForegroundColor Green
Write-Host ""
Write-Host "Comandos utiles:" -ForegroundColor Cyan
Write-Host "  Iniciar ahora  : Start-ScheduledTask -TaskName '$NombreTarea'"
Write-Host "  Ver estado     : Get-ScheduledTask -TaskName '$NombreTarea' | Select-Object State"
Write-Host "  Detener        : Stop-ScheduledTask  -TaskName '$NombreTarea'"
Write-Host "  Eliminar       : Unregister-ScheduledTask -TaskName '$NombreTarea' -Confirm:`$false"
Write-Host ""

# Iniciar inmediatamente
$iniciar = Read-Host "Iniciar el tunel ahora? (S/N)"
if ($iniciar -eq "S" -or $iniciar -eq "s") {
    Start-ScheduledTask -TaskName $NombreTarea
    Write-Host "[OK] Tunel iniciado." -ForegroundColor Green
}
