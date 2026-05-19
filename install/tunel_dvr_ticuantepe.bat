@echo off
REM ============================================================
REM tunel_dvr_ticuantepe.bat — Tunel SSH permanente DVR Ticuantepe
REM Sucursal: Ticuantepe | cod_sucursal: 20
REM Puerto VPS RTSP : 9590  (-> 192.168.1.200:554)
REM Puerto VPS HTTP : 9690  (-> 192.168.1.200:80)  ISAPI soportado
REM DVR: DS-7104HGHI-M1 Hikvision — firmware con ISAPI activo
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Ticuantepe...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9590:192.168.1.200:554 ^
    -R 0.0.0.0:9690:192.168.1.200:80 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
