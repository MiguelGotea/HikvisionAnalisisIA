@echo off
REM ============================================================
REM tunel_dvr_oficinas.bat — Tunel SSH permanente DVR Oficinas
REM Sucursal: Oficinas | cod_sucursal: 18
REM Puerto VPS RTSP : 9588  (-> 192.168.0.200:554)
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Oficinas...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9588:192.168.0.200:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
