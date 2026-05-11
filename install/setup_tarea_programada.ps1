# ============================================================
# setup_tarea_programada.ps1 — Crea tarea de Windows para el túnel SSH
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

# Eliminar tarea si ya existe (para actualizar)
$tareaExistente = Get-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue
if ($tareaExistente) {
    Write-Host "Eliminando tarea existente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $NombreTarea -Confirm:$false
}

# Definir la acción: ejecutar el .bat
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
Write-Host "✅ Tarea '$NombreTarea' creada correctamente." -ForegroundColor Green
Write-Host ""
Write-Host "Comandos utiles:" -ForegroundColor Cyan
Write-Host "  Iniciar ahora  : Start-ScheduledTask -TaskName '$NombreTarea'"
Write-Host "  Ver estado     : Get-ScheduledTask -TaskName '$NombreTarea' | Select-Object State"
Write-Host "  Detener        : Stop-ScheduledTask  -TaskName '$NombreTarea'"
Write-Host "  Eliminar       : Unregister-ScheduledTask -TaskName '$NombreTarea' -Confirm:`$false"
Write-Host ""

# Iniciar inmediatamente
$iniciar = Read-Host "¿Iniciar el tunel ahora? (S/N)"
if ($iniciar -eq "S" -or $iniciar -eq "s") {
    Start-ScheduledTask -TaskName $NombreTarea
    Write-Host "✅ Tunel iniciado." -ForegroundColor Green
}
