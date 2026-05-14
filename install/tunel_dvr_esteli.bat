@echo off
REM ============================================================
REM tunel_dvr_esteli.bat — Tunel SSH permanente DVR Esteli
REM Sucursal: Esteli | cod_sucursal: 5
REM Puerto VPS RTSP : 9575  (-> 192.168.1.50:554)
REM Puerto VPS HTTP : 9675  (-> 192.168.1.50:80)  ISAPI soportado
REM DVR: DVR-204F-F1 Hikvision — firmware con ISAPI activo
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
