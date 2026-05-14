@echo off
REM ============================================================
REM tunel_dvr_rivas.bat — Tunel SSH permanente DVR Rivas
REM Sucursal: Rivas | cod_sucursal: 17
REM Puerto VPS RTSP : 9587  (-> 192.168.40.170:554)
REM Puerto VPS HTTP : 9687  (-> 192.168.40.170:80)  ISAPI soportado
REM DVR: DVR-104G-M1 Hikvision — firmware con ISAPI activo
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Rivas...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9587:192.168.40.170:554 ^
    -R 0.0.0.0:9687:192.168.40.170:80 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
