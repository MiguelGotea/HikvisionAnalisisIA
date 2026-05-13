@echo off
REM ============================================================
REM tunel_dvr_lascolinas.bat — Tunel SSH permanente DVR Las Colinas
REM Sucursal: Las Colinas | cod_sucursal: 11
REM Puerto VPS RTSP : 9581  (-> 192.168.1.110:554)
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Las Colinas...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9581:192.168.1.110:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
