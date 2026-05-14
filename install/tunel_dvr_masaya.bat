@echo off
REM ============================================================
REM tunel_dvr_masaya.bat — Tunel SSH permanente DVR Masaya
REM Sucursal: Masaya | cod_sucursal: 12
REM Puerto VPS RTSP : 9582  (-> 192.168.1.120:554)
REM Puerto VPS HTTP : 9682  (-> 192.168.1.120:80)  ISAPI soportado
REM DVR: DS-7104HGHI-M1 Hikvision — firmware con ISAPI activo
REM ============================================================

:loop
echo [%date% %time%] Iniciando tunel SSH DVR Masaya...
ssh -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 0.0.0.0:9582:192.168.1.120:554 ^
    -R 0.0.0.0:9682:192.168.1.120:80 ^
    root@198.211.97.243 -N

echo [%date% %time%] Tunel caido. Reconectando en 10 segundos...
timeout /t 10 /nobreak >nul
goto loop
