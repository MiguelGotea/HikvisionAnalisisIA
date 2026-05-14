-- ============================================================
-- alter_dvr_sucursales.sql
-- Configuracion completa de DVR_Sucursales para el sistema
-- de captura de imagenes via tunel SSH.
--
-- Ejecutar en: base de datos del ERP (u83b9374897_erp)
-- Fecha:       2026-05-03 | Actualizado: 2026-05-14
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
-- Convencion: puerto_http_vps = puerto_rtsp_vps + 100 (para todos)
--
-- El tunel HTTP permite acceso a ISAPI (snapshot instantaneo).
-- Si el DVR no responde en el puerto HTTP, el sistema cae a RTSP.
-- ------------------------------------------------------------

-- Leon (cod:2)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9552, `puerto_http_vps` = 9652, `tunel_activo` = 0
WHERE `cod_sucursal` = 2;

-- Matagalpa (cod:4)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9574, `puerto_http_vps` = 9674, `tunel_activo` = 0
WHERE `cod_sucursal` = 4;

-- Esteli (cod:5)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9575, `puerto_http_vps` = 9675, `tunel_activo` = 0
WHERE `cod_sucursal` = 5;

-- Altamira (cod:7)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9577, `puerto_http_vps` = 9677, `tunel_activo` = 0
WHERE `cod_sucursal` = 7;

-- Villa Fontana (cod:9) — ACTIVO: tunel instalado y funcionando
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9579, `puerto_http_vps` = 9679, `tunel_activo` = 1
WHERE `cod_sucursal` = 9;

-- Granada (cod:10) — ACTIVO: tunel RTSP (9554) + HTTP (9654) funcionando
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9554, `puerto_http_vps` = 9654, `tunel_activo` = 1
WHERE `cod_sucursal` = 10;

-- Las Colinas (cod:11)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9581, `puerto_http_vps` = 9681, `tunel_activo` = 0
WHERE `cod_sucursal` = 11;

-- Masaya (cod:12)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9582, `puerto_http_vps` = 9682, `tunel_activo` = 0
WHERE `cod_sucursal` = 12;

-- Natura (cod:13)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9583, `puerto_http_vps` = 9683, `tunel_activo` = 0
WHERE `cod_sucursal` = 13;

-- Las Brisas (cod:16)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9561, `puerto_http_vps` = 9661, `tunel_activo` = 0
WHERE `cod_sucursal` = 16;

-- Rivas (cod:17)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9587, `puerto_http_vps` = 9687, `tunel_activo` = 0
WHERE `cod_sucursal` = 17;

-- Oficinas (cod:18)
UPDATE `DVR_Sucursales`
SET `puerto_rtsp_vps` = 9588, `puerto_http_vps` = 9688, `tunel_activo` = 0
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
