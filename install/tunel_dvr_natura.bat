@echo off
REM ============================================================
REM tunel_dvr_natura.bat — Tunel SSH permanente DVR Natura
REM Sucursal: Natura | cod_sucursal: 13
REM Puerto VPS RTSP : 9583  (-> 192.168.1.130:554)
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Natura...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9583:192.168.1.130:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
