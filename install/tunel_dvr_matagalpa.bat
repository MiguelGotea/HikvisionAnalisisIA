@echo off
REM ============================================================
REM tunel_dvr_matagalpa.bat — Tunel SSH permanente DVR Matagalpa
REM Sucursal: Matagalpa | cod_sucursal: 4
REM Puerto VPS RTSP : 9574  (-> 192.168.1.40:554)
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Matagalpa...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9574:192.168.1.40:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
