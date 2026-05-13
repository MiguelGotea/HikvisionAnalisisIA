@echo off
REM ============================================================
REM tunel_dvr_lasbrisas.bat — Tunel SSH permanente DVR Las Brisas
REM Sucursal: Las Brisas | cod_sucursal: 16
REM Puerto VPS RTSP : 9561  (-> 192.168.0.160:554)
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Las Brisas...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9561:192.168.0.160:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
