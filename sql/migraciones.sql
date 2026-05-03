-- ============================================================
-- MIGRACIONES HikvisionAnalisisIA
-- Base de datos: u839374897_erp (Hostinger)
-- Ejecutar en orden
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. Nuevas columnas en DVR_Sucursales
-- ────────────────────────────────────────────────────────────
ALTER TABLE DVR_Sucursales
  ADD COLUMN IF NOT EXISTS canal_caja      INT            DEFAULT NULL COMMENT 'Track RTSP del canal de caja (101=ch1, 201=ch2, 401=ch4)',
  ADD COLUMN IF NOT EXISTS puerto_rtsp_vps INT            DEFAULT NULL COMMENT 'Puerto RTSP expuesto en VPS via túnel SSH inverso',
  ADD COLUMN IF NOT EXISTS tunel_activo    TINYINT(1)     DEFAULT 0    COMMENT '1=Túnel SSH configurado y activo en producción';

-- Datos iniciales de Granada (cod_sucursal=10, único tunel probado)
UPDATE DVR_Sucursales
SET
  canal_caja      = 101,
  puerto_rtsp_vps = 9554,
  tunel_activo    = 1
WHERE cod_sucursal = 10;

-- Puertos reservados para las demás sucursales (sin túnel aún)
-- Masaya=9555, Central=9556, Estelí=9557, Calli=9558, VillaFontana=9559, León=9560
-- Actualizar puerto_rtsp_vps y canal_caja por cada sucursal cuando se configure su túnel.


-- ────────────────────────────────────────────────────────────
-- 2. Cola de análisis (queue table)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hikvision_cola_analisis (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  cod_pedido      INT          NOT NULL                   COMMENT 'CodPedido de VentasGlobalesAccessCSV',
  local_codigo    VARCHAR(11)  NOT NULL                   COMMENT 'Mismo valor que VentasGlobalesAccessCSV.local',
  fecha           DATE         NOT NULL                   COMMENT 'Fecha del pedido (Nicaragua)',
  hora_inicio     TIME         NOT NULL                   COMMENT 'HoraCreado Nicaragua — se convierte a UTC al descargar',
  hora_fin        TIME         NOT NULL                   COMMENT 'HoraImpreso Nicaragua — se convierte a UTC al descargar',
  canal_track     INT          NOT NULL                   COMMENT 'Track RTSP copiado de DVR_Sucursales.canal_caja',
  puerto_rtsp     INT          NOT NULL                   COMMENT 'Puerto VPS copiado de DVR_Sucursales.puerto_rtsp_vps',
  dvr_ip_local    VARCHAR(50)  NOT NULL                   COMMENT 'IP local del DVR (portal_ip_local)',
  dvr_usuario     VARCHAR(100) NOT NULL,
  dvr_clave       VARCHAR(255) NOT NULL,
  vps_ip          VARCHAR(50)  NOT NULL DEFAULT '198.211.97.243',
  estado          ENUM('pendiente','procesando','completado','fallido')
                               NOT NULL DEFAULT 'pendiente',
  tipo            ENUM('automatico','manual')
                               NOT NULL DEFAULT 'automatico'  COMMENT 'automatico=cola del día / manual=pedido puntual',
  prioridad       TINYINT      NOT NULL DEFAULT 5            COMMENT '1=urgente (manual), 5=normal (auto)',
  intentos        TINYINT      NOT NULL DEFAULT 0,
  error_mensaje   TEXT             DEFAULT NULL,
  created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_estado_cola  (estado, prioridad, created_at),
  INDEX idx_cod_pedido   (cod_pedido),
  INDEX idx_local_fecha  (local_codigo, fecha),
  INDEX idx_fecha        (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Cola de videos DVR pendientes de análisis IA';


-- ────────────────────────────────────────────────────────────
-- 3. Tabla de resultados de análisis
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hikvision_analisis_ia_atencion (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  id_cola           INT          NOT NULL                   COMMENT 'FK a hikvision_cola_analisis',
  cod_pedido        INT          NOT NULL,
  local_codigo      VARCHAR(11)  NOT NULL,
  sucursal_nombre   VARCHAR(50)      DEFAULT NULL,
  fecha             DATE         NOT NULL,
  hora_inicio       TIME         NOT NULL,
  hora_fin          TIME         NOT NULL,

  -- Calificaciones 1-10 por categoría
  cal_amabilidad    TINYINT UNSIGNED DEFAULT NULL COMMENT '1-10: trato amable al cliente',
  cal_saludo        TINYINT UNSIGNED DEFAULT NULL COMMENT '1-10: saludo inicial correcto',
  cal_despedida     TINYINT UNSIGNED DEFAULT NULL COMMENT '1-10: despedida al cliente',
  cal_membresia     TINYINT UNSIGNED DEFAULT NULL COMMENT '1-10: ofreció membresía/puntos',
  promedio          DECIMAL(4,2)     DEFAULT NULL COMMENT 'Promedio de las 4 categorías',

  resumen           TEXT             DEFAULT NULL COMMENT 'Resumen del análisis en español',
  tiene_audio       TINYINT(1)       DEFAULT 0,
  duracion_segundos INT              DEFAULT NULL,
  modelo_ia         VARCHAR(100)     DEFAULT NULL COMMENT 'Modelo Gemini usado',
  created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_cod_pedido   (cod_pedido),
  INDEX idx_local_fecha  (local_codigo, fecha),
  INDEX idx_fecha        (fecha),
  INDEX idx_promedio     (promedio),
  CONSTRAINT fk_analisis_cola
    FOREIGN KEY (id_cola) REFERENCES hikvision_cola_analisis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Resultados de análisis de atención al cliente por IA';
