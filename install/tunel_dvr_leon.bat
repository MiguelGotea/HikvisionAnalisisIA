@echo off
REM ============================================================
REM tunel_dvr_leon.bat — Tunel SSH permanente DVR Leon
REM Sucursal: Leon | cod_sucursal: 2
REM Puerto VPS RTSP : 9552  (-> 192.168.1.20:554)
REM Puerto VPS HTTP : 9652  (-> 192.168.1.20:80 )  para captura de imagen ISAPI
REM DVR IP local: 192.168.1.20 (actualiza si cambia)
REM ============================================================
REM
REM INSTALACION:
REM 1. Coloca este archivo en C:\tunel_dvr_leon.bat
REM 2. Ejecuta setup_tarea_programada.ps1 como Administrador
REM    para crear la tarea que lo inicia automaticamente.
REM
REM Para probar manualmente: doble clic o ejecutar en CMD
REM Para detener: cerrar la ventana o Ctrl+C
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Leon...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9552:192.168.1.20:554 ^
    -R 0.0.0.0:9652:192.168.1.20:80 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
