@echo off
REM ============================================================
REM tunel_dvr_esteli.bat — Tunel SSH permanente DVR Esteli
REM Sucursal: Esteli | cod_sucursal: 5
REM Puerto VPS RTSP : 9575  (-> 192.168.1.50:554)
REM Puerto VPS HTTP : 9675  (-> 192.168.1.50:80 )  para captura de imagen ISAPI
REM DVR IP local: 192.168.1.50 (actualiza si cambia)
REM ============================================================
REM
REM INSTALACION:
REM 1. Coloca este archivo en C:\tunel_dvr_esteli.bat
REM 2. Ejecuta setup_tarea_programada.ps1 como Administrador
REM    para crear la tarea que lo inicia automaticamente.
REM
REM Para probar manualmente: doble clic o ejecutar en CMD
REM Para detener: cerrar la ventana o Ctrl+C
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Esteli...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9575:192.168.1.50:554 ^
    -R 0.0.0.0:9675:192.168.1.50:80 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
