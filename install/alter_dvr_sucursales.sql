-- ============================================================
-- alter_dvr_sucursales.sql
-- Agrega las columnas de túnel SSH a DVR_Sucursales
-- y establece los puertos RTSP de cada sucursal.
--
-- Ejecutar en: base de datos del ERP (u83b9374897_erp)
-- Fecha:       2026-05-03
-- ============================================================

-- ------------------------------------------------------------
-- 1. Agregar columnas nuevas (si no existen)
-- ------------------------------------------------------------

ALTER TABLE `DVR_Sucursales`
    ADD COLUMN IF NOT EXISTS `puerto_rtsp_vps` int(11) DEFAULT NULL
        COMMENT 'Puerto RTSP expuesto en VPS via túnel SSH inverso'
        AFTER `canal_caja`,
    ADD COLUMN IF NOT EXISTS `tunel_activo` tinyint(1) DEFAULT 0
        COMMENT '1=Túnel SSH configurado y activo en producción'
        AFTER `puerto_rtsp_vps`;

-- ------------------------------------------------------------
-- 2. Asignar puertos RTSP (puerto = 955X donde X = cod_sucursal
--    o 958X para sucursales de dos dígitos sin colisión)
--    Estos puertos deben coincidir exactamente con los archivos
--    tunel_dvr_*.bat de la carpeta install/
-- ------------------------------------------------------------

-- León (cod:2) → tunel_dvr_leon.bat          puerto 9552
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9552, `tunel_activo` = 0 WHERE `cod_sucursal` = 2;

-- Matagalpa (cod:4) → tunel_dvr_matagalpa.bat  puerto 9574
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9574, `tunel_activo` = 0 WHERE `cod_sucursal` = 4;

-- Estelí (cod:5) → tunel_dvr_esteli.bat        puerto 9575
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9575, `tunel_activo` = 0 WHERE `cod_sucursal` = 5;

-- Altamira (cod:7) → tunel_dvr_altamira.bat    puerto 9577
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9577, `tunel_activo` = 0 WHERE `cod_sucursal` = 7;

-- Villa Fontana (cod:9) → tunel_dvr_villafontana.bat  puerto 9579
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9579, `tunel_activo` = 0 WHERE `cod_sucursal` = 9;

-- Granada (cod:10) → tunel_dvr_granada.bat     puerto 9554  ← YA ACTIVO
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9554, `tunel_activo` = 1 WHERE `cod_sucursal` = 10;

-- Las Colinas (cod:11) → tunel_dvr_lascolinas.bat  puerto 9581
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9581, `tunel_activo` = 0 WHERE `cod_sucursal` = 11;

-- Masaya (cod:12) → tunel_dvr_masaya.bat       puerto 9582
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9582, `tunel_activo` = 0 WHERE `cod_sucursal` = 12;

-- Natura (cod:13) → tunel_dvr_natura.bat       puerto 9583
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9583, `tunel_activo` = 0 WHERE `cod_sucursal` = 13;

-- Las Brisas (cod:16) → tunel_dvr_lasbrisas.bat  puerto 9561  ← YA ACTIVO
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9561, `tunel_activo` = 1 WHERE `cod_sucursal` = 16;

-- Rivas (cod:17) → tunel_dvr_rivas.bat         puerto 9587
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9587, `tunel_activo` = 0 WHERE `cod_sucursal` = 17;

-- Oficinas (cod:18) → tunel_dvr_oficinas.bat   puerto 9588
UPDATE `DVR_Sucursales` SET `puerto_rtsp_vps` = 9588, `tunel_activo` = 0 WHERE `cod_sucursal` = 18;

-- ------------------------------------------------------------
-- 3. Verificar resultado
-- ------------------------------------------------------------
SELECT
    cod_sucursal,
    nombre_sucursal,
    portal_ip_local,
    puerto_rtsp_vps,
    tunel_activo,
    CONCAT('rtsp://198.211.97.243:', puerto_rtsp_vps, '/Streaming/Channels/101') AS url_rtsp_vps
FROM `DVR_Sucursales`
WHERE puerto_rtsp_vps IS NOT NULL
ORDER BY cod_sucursal;
