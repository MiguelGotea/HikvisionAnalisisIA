@echo off
REM ============================================================
REM tunel_dvr_rivas.bat — Túnel SSH permanente DVR Rivas
REM Sucursal: Rivas | cod_sucursal: 17
REM Puerto VPS RTSP: 9587
REM DVR IP local: 192.168.40.170 (actualiza si cambia)
REM ============================================================
REM
REM INSTALACIÓN:
REM 1. Coloca este archivo en C:\tunel_dvr_rivas.bat
REM 2. Ejecuta setup_tarea_programada.ps1 como Administrador
REM    para crear la tarea que lo inicia automáticamente.
REM
REM Para probar manualmente: doble clic o ejecutar en CMD
REM Para detener: cerrar la ventana o Ctrl+C
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Rivas...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9587:192.168.40.170:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
