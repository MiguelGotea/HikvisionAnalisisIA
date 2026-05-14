-- ============================================================
-- alter_dvr_sucursales.sql
-- Configuracion completa de DVR_Sucursales para el sistema
-- de captura de imagenes via tunel SSH.
--
-- Ejecutar en: base de datos del ERP (u83b9374897_erp)
-- Fecha:       2026-05-03 | Actualizado: 2026-05-13
-- ============================================================

-- ------------------------------------------------------------
-- 1. Agregar columnas (idempotente - no falla si ya existen)
-- ------------------------------------------------------------

ALTER TABLE `DVR_Sucursales`
    ADD COLUMN IF NOT EXISTS `puerto_rtsp_vps` int(11) DEFAULT NULL
        COMMENT 'Puerto RTSP en VPS via tunel SSH inverso (ej: 9579 -> DVR:554)'
        AFTER `canal_caja`,
    ADD COLUMN IF NOT EXISTS `puerto_http_vps` int(11) DEFAULT NULL
        COMMENT 'Puerto HTTP en VPS para ISAPI snapshot (DVR moderno). NULL = usar RTSP. Convencion: puerto_rtsp_vps + 100'
        AFTER `puerto_rtsp_vps`,
    ADD COLUMN IF NOT EXISTS `tunel_activo` tinyint(1) DEFAULT 0
        COMMENT '1 = tunel SSH instalado y activo en produccion'
        AFTER `puerto_http_vps`;

-- ------------------------------------------------------------
-- 2. Puertos por sucursal
--
-- puerto_http_vps:
--   NULL = DVR firmware antiguo (DS-7104HGHI-M1, etc.) → solo RTSP
--   >0   = DVR moderno con ISAPI → imagen en vivo instantanea
--
-- Para verificar si un DVR soporta ISAPI, abrir en el navegador
-- desde la red local de la sucursal:
--   http://admin:CLAVE@DVR_IP:80/ISAPI/Streaming/channels/101/picture
-- ------------------------------------------------------------

-- Leon (cod:2) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9552, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 2;

-- Matagalpa (cod:4) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9574, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 4;

-- Esteli (cod:5) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9575, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 5;

-- Altamira (cod:7) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9577, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 7;

-- Villa Fontana (cod:9) — DS-7104HGHI-M1, firmware SIN ISAPI → solo RTSP
-- ACTIVO: tunel instalado y funcionando
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9579, `puerto_http_vps` = NULL, `tunel_activo` = 1
WHERE `cod_sucursal` = 9;

-- Granada (cod:10) — DVR-104G-K1, firmware CON ISAPI → imagen en vivo
-- ACTIVO: tunel RTSP (9554) + HTTP (9654) instalados y funcionando
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9554, `puerto_http_vps` = 9654, `tunel_activo` = 1
WHERE `cod_sucursal` = 10;

-- Las Colinas (cod:11) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9581, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 11;

-- Masaya (cod:12) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9582, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 12;

-- Natura (cod:13) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9583, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 13;

-- Las Brisas (cod:16) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9561, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 16;

-- Rivas (cod:17) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9587, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 17;

-- Oficinas (cod:18) — firmware por verificar
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9588, `puerto_http_vps` = NULL, `tunel_activo` = 0
WHERE `cod_sucursal` = 18;

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
    CASE
        WHEN puerto_http_vps IS NOT NULL THEN 'ISAPI (live)'
        ELSE 'RTSP (~5 min lag)'
    END AS metodo_snapshot
FROM `DVR_Sucursales`
WHERE puerto_rtsp_vps IS NOT NULL
ORDER BY cod_sucursal;
