-- ============================================================
-- alter_dvr_sucursales.sql
-- Agrega las columnas de tunel SSH a DVR_Sucursales
-- y establece los puertos RTSP y HTTP de cada sucursal.
--
-- Ejecutar en: base de datos del ERP (u83b9374897_erp)
-- Fecha:       2026-05-03 | Actualizado: 2026-05-13
-- ============================================================

-- ------------------------------------------------------------
-- 1. Agregar columnas nuevas (si no existen)
-- ------------------------------------------------------------

ALTER TABLE `DVR_Sucursales`
    ADD COLUMN IF NOT EXISTS `puerto_rtsp_vps` int(11) DEFAULT NULL
        COMMENT 'Puerto RTSP expuesto en VPS via tunel SSH inverso (ej: 9579)'
        AFTER `canal_caja`,
    ADD COLUMN IF NOT EXISTS `puerto_http_vps` int(11) DEFAULT NULL
        COMMENT 'Puerto HTTP expuesto en VPS via tunel SSH inverso = puerto_rtsp_vps + 100 (ej: 9679). Usado por dvr_capturar_imagen.php para ISAPI snapshot'
        AFTER `puerto_rtsp_vps`,
    ADD COLUMN IF NOT EXISTS `tunel_activo` tinyint(1) DEFAULT 0
        COMMENT '1=Tunel SSH configurado y activo en produccion'
        AFTER `puerto_http_vps`;

-- ------------------------------------------------------------
-- 2. Asignar puertos por sucursal
--    RTSP = puerto original de cada .bat
--    HTTP = RTSP + 100  (regla fija para todo el sistema)
-- ------------------------------------------------------------

-- Leon (cod:2) → tunel_dvr_leon.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9552, `puerto_http_vps` = 9652, `tunel_activo` = 0 WHERE `cod_sucursal` = 2;

-- Matagalpa (cod:4) → tunel_dvr_matagalpa.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9574, `puerto_http_vps` = 9674, `tunel_activo` = 0 WHERE `cod_sucursal` = 4;

-- Esteli (cod:5) → tunel_dvr_esteli.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9575, `puerto_http_vps` = 9675, `tunel_activo` = 0 WHERE `cod_sucursal` = 5;

-- Altamira (cod:7) → tunel_dvr_altamira.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9577, `puerto_http_vps` = 9677, `tunel_activo` = 0 WHERE `cod_sucursal` = 7;

-- Villa Fontana (cod:9) → tunel_dvr_villafontana.bat  ← YA ACTIVO
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9579, `puerto_http_vps` = 9679, `tunel_activo` = 1 WHERE `cod_sucursal` = 9;

-- Granada (cod:10) → tunel_dvr_granada.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9554, `puerto_http_vps` = 9654, `tunel_activo` = 0 WHERE `cod_sucursal` = 10;

-- Las Colinas (cod:11) → tunel_dvr_lascolinas.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9581, `puerto_http_vps` = 9681, `tunel_activo` = 0 WHERE `cod_sucursal` = 11;

-- Masaya (cod:12) → tunel_dvr_masaya.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9582, `puerto_http_vps` = 9682, `tunel_activo` = 0 WHERE `cod_sucursal` = 12;

-- Natura (cod:13) → tunel_dvr_natura.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9583, `puerto_http_vps` = 9683, `tunel_activo` = 0 WHERE `cod_sucursal` = 13;

-- Las Brisas (cod:16) → tunel_dvr_lasbrisas.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9561, `puerto_http_vps` = 9661, `tunel_activo` = 0 WHERE `cod_sucursal` = 16;

-- Rivas (cod:17) → tunel_dvr_rivas.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9587, `puerto_http_vps` = 9687, `tunel_activo` = 0 WHERE `cod_sucursal` = 17;

-- Oficinas (cod:18) → tunel_dvr_oficinas.bat
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9588, `puerto_http_vps` = 9688, `tunel_activo` = 0 WHERE `cod_sucursal` = 18;

-- ------------------------------------------------------------
-- 3. Verificar resultado
-- ------------------------------------------------------------
SELECT
    cod_sucursal,
    nombre_sucursal,
    portal_ip_local,
    puerto_rtsp_vps,
    puerto_http_vps,
    tunel_activo,
    CONCAT('rtsp://198.211.97.243:', puerto_rtsp_vps, '/PSIA/Streaming/tracks/101') AS url_rtsp_vps,
    CONCAT('http://198.211.97.243:', puerto_http_vps, '/ISAPI/Streaming/channels/101/picture') AS url_http_vps
FROM `DVR_Sucursales`
WHERE puerto_rtsp_vps IS NOT NULL
ORDER BY cod_sucursal;
