@echo off
REM ============================================================
REM tunel_dvr_leon.bat — Tunel SSH permanente DVR Leon
REM Sucursal: Leon | cod_sucursal: 2
REM Puerto VPS RTSP : 9552  (-> 192.168.1.20:554)
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Leon...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9552:192.168.1.20:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
