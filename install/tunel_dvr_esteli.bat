@echo off
REM ============================================================
REM tunel_dvr_esteli.bat — Tunel SSH permanente DVR Esteli
REM Sucursal: Esteli | cod_sucursal: 5
REM Puerto VPS RTSP : 9575  (-> 192.168.1.50:554)
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Esteli...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9575:192.168.1.50:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
