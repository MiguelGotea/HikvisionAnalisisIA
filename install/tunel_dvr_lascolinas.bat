@echo off
REM ============================================================
REM tunel_dvr_lascolinas.bat — Túnel SSH permanente DVR Las Colinas
REM Sucursal: Las Colinas | cod_sucursal: 11
REM Puerto VPS RTSP: 9581
REM DVR IP local: 192.168.1.110 (actualiza si cambia)
REM ============================================================
REM
REM INSTALACIÓN:
REM 1. Coloca este archivo en C:\tunel_dvr_lascolinas.bat
REM 2. Ejecuta setup_tarea_programada.ps1 como Administrador
REM    para crear la tarea que lo inicia automáticamente.
REM
REM Para probar manualmente: doble clic o ejecutar en CMD
REM Para detener: cerrar la ventana o Ctrl+C
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Las Colinas...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9581:192.168.1.110:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
