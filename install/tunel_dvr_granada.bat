@echo off
REM ============================================================
REM tunel_dvr_granada.bat — Tunel SSH permanente DVR Granada
REM Sucursal: Granada | cod_sucursal: 10
REM Puerto VPS RTSP : 9554  (-> 192.168.1.100:554)
REM Puerto VPS HTTP : 9654  (-> 192.168.1.100:80 )  para captura de imagen ISAPI
REM DVR IP local: 192.168.1.100 (actualiza si cambia)
REM ============================================================
REM
REM INSTALACION:
REM 1. Coloca este archivo en C:\tunel_dvr_granada.bat
REM 2. Ejecuta setup_tarea_programada.ps1 como Administrador
REM    para crear la tarea que lo inicia automaticamente.
REM
REM Para probar manualmente: doble clic o ejecutar en CMD
REM Para detener: cerrar la ventana o Ctrl+C
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Granada...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9554:192.168.1.100:554 ^
    -R 0.0.0.0:9654:192.168.1.100:80 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
