@echo off
REM ============================================================
REM tunel_dvr_oficinas.bat — Tunel SSH permanente DVR Oficinas
REM Sucursal: Oficinas | cod_sucursal: 18
REM Puerto VPS RTSP : 9588  (-> 192.168.0.200:554)
REM Puerto VPS HTTP : 9688  (-> 192.168.0.200:80 )  para captura de imagen ISAPI
REM DVR IP local: 192.168.0.200 (actualiza si cambia)
REM ============================================================
REM
REM INSTALACION:
REM 1. Coloca este archivo en C:\tunel_dvr_oficinas.bat
REM 2. Ejecuta setup_tarea_programada.ps1 como Administrador
REM    para crear la tarea que lo inicia automaticamente.
REM
REM Para probar manualmente: doble clic o ejecutar en CMD
REM Para detener: cerrar la ventana o Ctrl+C
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Oficinas...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9588:192.168.0.200:554 ^
    -R 0.0.0.0:9688:192.168.0.200:80 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
