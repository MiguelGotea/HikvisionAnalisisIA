@echo off
REM ============================================================
REM tunel_dvr_villafontana.bat — Tunel SSH permanente DVR Villa Fontana
REM Sucursal: Villa Fontana | cod_sucursal: 9
REM Puerto VPS RTSP : 9579  (-> 192.168.1.90:554)
REM Puerto VPS HTTP : 9679  (-> 192.168.1.90:80)  ISAPI soportado
REM DVR: DS-7104HGHI-M1 Hikvision — firmware con ISAPI activo
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Villa Fontana...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9579:192.168.1.90:554 ^
    -R 0.0.0.0:9679:192.168.1.90:80 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
