@echo off
REM ============================================================
REM tunel_dvr_altamira.bat — Tunel SSH permanente DVR Altamira
REM Sucursal: Altamira | cod_sucursal: 7
REM Puerto VPS RTSP : 9577  (-> 192.168.1.70:554)
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Altamira...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9577:192.168.1.70:554 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
