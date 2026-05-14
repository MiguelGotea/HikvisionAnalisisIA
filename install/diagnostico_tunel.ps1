# ============================================================
# diagnostico_tunel.ps1 — Diagnostico automatico del tunel SSH DVR
# Ejecutar como ADMINISTRADOR en PowerShell
#
# Uso:
#   .\diagnostico_tunel.ps1 -NombreTarea "TunelDVR_Granada" -BatPath "C:\tunel_dvr_granada.bat" -PuertoVPS 9554 -IPVPS "198.211.97.243"
# ============================================================

param(
    [string]$NombreTarea = "TunelDVR_Granada",
    [string]$BatPath     = "C:\tunel_dvr_granada.bat",
    [int]   $PuertoVPS   = 9554,
    [string]$IPVPS       = "198.211.97.243"
)

$OK  = "[OK]  "
$ERR = "[ERR] "
$INF = "[INFO]"
$WARN= "[WARN]"

function Write-OK   { param($m) Write-Host "$OK $m"   -ForegroundColor Green }
function Write-Err  { param($m) Write-Host "$ERR $m"  -ForegroundColor Red }
function Write-Inf  { param($m) Write-Host "$INF $m"  -ForegroundColor Cyan }
function Write-Warn { param($m) Write-Host "$WARN $m" -ForegroundColor Yellow }

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSTICO TUNEL SSH — $NombreTarea"                    -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"               -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$errores = 0

# ----------------------------------------------------------
# 1. Archivo .bat
# ----------------------------------------------------------
Write-Inf "PASO 1 — Archivo .bat [$BatPath]"
if (Test-Path $BatPath) {
    Write-OK  "Archivo existe: $BatPath"
} else {
    Write-Err "NO existe: $BatPath"
    Write-Warn "  Copia el .bat a esa ruta. Ejemplo:"
    Write-Host "  Copy-Item 'C:\Users\Pitaya\Google Drive BP\...\tunel_dvr_granada.bat' 'C:\'" -ForegroundColor Gray
    $errores++
}
Write-Host ""

# ----------------------------------------------------------
# 2. OpenSSH instalado
# ----------------------------------------------------------
Write-Inf "PASO 2 — OpenSSH disponible en PATH"
$sshPath = Get-Command ssh -ErrorAction SilentlyContinue
if ($sshPath) {
    Write-OK "SSH encontrado: $($sshPath.Source)"
} else {
    Write-Err "ssh.exe NO encontrado en PATH"
    Write-Warn "  Instalar OpenSSH: Configuracion > Apps > Caracteristicas opcionales > OpenSSH Client"
    $errores++
}
Write-Host ""

# ----------------------------------------------------------
# 3. Llave SSH del usuario actual
# ----------------------------------------------------------
Write-Inf "PASO 3 — Llave SSH usuario actual"
$llaveUsuario = "$env:USERPROFILE\.ssh\id_ed25519"
if (Test-Path $llaveUsuario) {
    Write-OK "Llave encontrada: $llaveUsuario"
} else {
    Write-Err "NO existe llave en: $llaveUsuario"
    Write-Warn "  Generar con: ssh-keygen -t ed25519 -C 'granada'"
    Write-Warn "  Luego registrar en el VPS: authorized_keys"
    $errores++
}
Write-Host ""

# ----------------------------------------------------------
# 4. Llave SSH del perfil SYSTEM
# ----------------------------------------------------------
Write-Inf "PASO 4 — Llave SSH perfil SYSTEM (requerido para la tarea)"
$systemSsh  = "C:\Windows\System32\config\systemprofile\.ssh"
$systemKey  = "$systemSsh\id_ed25519"
$systemKH   = "$systemSsh\known_hosts"

if (Test-Path $systemKey) {
    Write-OK "Llave SYSTEM OK: $systemKey"
} else {
    Write-Err "Llave NO existe para SYSTEM: $systemKey"
    Write-Warn "  Solucion: volver a ejecutar setup_tarea_programada.ps1 como Admin"
    $errores++
}

if (Test-Path $systemKH) {
    $khContent = Get-Content $systemKH -Raw
    if ([string]::IsNullOrWhiteSpace($khContent)) {
        Write-Err "known_hosts de SYSTEM esta VACIO — SSH no puede confirmar el host"
        Write-Warn "  Solucion (ejecutar como Admin):"
        Write-Warn "    Copy-Item '$env:USERPROFILE\.ssh\known_hosts' '$systemKH' -Force"
        $errores++
    } else {
        if ($khContent -match [regex]::Escape($IPVPS)) {
            Write-OK "known_hosts contiene la entrada del VPS ($IPVPS)"
        } else {
            Write-Warn "known_hosts existe pero NO contiene $IPVPS"
            Write-Warn "  Prueba el SSH manual primero para registrar el host, luego copia:"
            Write-Warn "    Copy-Item '$env:USERPROFILE\.ssh\known_hosts' '$systemKH' -Force"
            $errores++
        }
    }
} else {
    Write-Err "known_hosts de SYSTEM NO existe"
    Write-Warn "  Solucion (ejecutar como Admin):"
    Write-Warn "    Copy-Item '$env:USERPROFILE\.ssh\known_hosts' '$systemKH' -Force"
    $errores++
}
Write-Host ""

# ----------------------------------------------------------
# 5. Estado de la tarea programada
# ----------------------------------------------------------
Write-Inf "PASO 5 — Tarea programada [$NombreTarea]"
$tarea = Get-ScheduledTask -TaskName $NombreTarea -ErrorAction SilentlyContinue
if (-not $tarea) {
    Write-Err "Tarea '$NombreTarea' NO encontrada en el sistema"
    Write-Warn "  Ejecutar setup_tarea_programada.ps1 como Admin para instalarla"
    $errores++
} else {
    $estado = $tarea.State
    switch ($estado) {
        "Running"  { Write-OK   "Tarea en estado: RUNNING (tunel activo)" }
        "Ready"    { Write-Warn "Tarea en estado: READY (no esta corriendo ahora)" }
        "Disabled" { Write-Err  "Tarea en estado: DISABLED (fue deshabilitada)"; $errores++ }
        default    { Write-Warn "Tarea en estado: $estado" }
    }

    $info = Get-ScheduledTaskInfo -TaskName $NombreTarea -ErrorAction SilentlyContinue
    if ($info) {
        Write-Host "  Ultima ejecucion : $($info.LastRunTime)" -ForegroundColor Gray
        Write-Host "  Codigo resultado : $($info.LastTaskResult)  (0 = exito)" -ForegroundColor Gray
        if ($info.LastTaskResult -ne 0 -and $info.LastTaskResult -ne $null) {
            Write-Warn "  Codigo de error no-cero: $($info.LastTaskResult)"
            Write-Warn "  Ver logs: Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' | Where-Object { `$_.Message -like '*$NombreTarea*' } | Select-Object -First 10 TimeCreated, Message | Format-List"
            $errores++
        }
    }
}
Write-Host ""

# ----------------------------------------------------------
# 6. Conectividad de red al VPS (ping TCP 22)
# ----------------------------------------------------------
Write-Inf "PASO 6 — Conectividad al VPS $IPVPS puerto 22"
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $conn = $tcp.BeginConnect($IPVPS, 22, $null, $null)
    $ok   = $conn.AsyncWaitHandle.WaitOne(3000, $false)
    if ($ok -and $tcp.Connected) {
        Write-OK "Puerto 22 alcanzable en $IPVPS — red OK"
        $tcp.Close()
    } else {
        Write-Err "No se puede conectar al VPS $IPVPS`:22 — verificar internet / firewall local"
        $errores++
    }
} catch {
    Write-Err "Error de red: $_"
    $errores++
}
Write-Host ""

# ----------------------------------------------------------
# 7. Resumen y acciones sugeridas
# ----------------------------------------------------------
Write-Host "==========================================================" -ForegroundColor Cyan
if ($errores -eq 0) {
    Write-Host "  RESULTADO: Sin errores detectados localmente." -ForegroundColor Green
    Write-Host "  Si el tunel aun no funciona, verificar en el VPS:" -ForegroundColor Green
    Write-Host "    ss -tlnp | grep $PuertoVPS"                       -ForegroundColor Gray
    Write-Host "    ufw status | grep $PuertoVPS"                     -ForegroundColor Gray
} else {
    Write-Host "  RESULTADO: $errores problema(s) detectado(s). Ver arriba." -ForegroundColor Red
}
Write-Host ""
Write-Host "  Comandos de control rapido:" -ForegroundColor Cyan
Write-Host "    Iniciar : Start-ScheduledTask -TaskName '$NombreTarea'" -ForegroundColor Gray
Write-Host "    Estado  : Get-ScheduledTask   -TaskName '$NombreTarea' | Select-Object State" -ForegroundColor Gray
Write-Host "    Detener : Stop-ScheduledTask  -TaskName '$NombreTarea'" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
