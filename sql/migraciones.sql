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

-- Datos iniciales de Granada (cod_sucursal=10)
UPDATE DVR_Sucursales
SET canal_caja = 101, puerto_rtsp_vps = 9554, tunel_activo = 1
WHERE cod_sucursal = 10;

-- Las Brisas (cod_sucursal=16)
UPDATE DVR_Sucursales
SET canal_caja = 101, puerto_rtsp_vps = 9561, tunel_activo = 1
WHERE cod_sucursal = 16;

-- Puertos reservados para las demás sucursales (sin túnel aún)
-- Masaya=9555, Central=9556, Estelí=9557, Calli=9558, VillaFontana=9559, León=9560


-- ────────────────────────────────────────────────────────────
-- 2. Cola de análisis (queue table) — sin cambios
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hikvision_cola_analisis (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  cod_pedido      INT          NOT NULL                   COMMENT 'CodPedido de VentasGlobalesAccessCSV',
  local_codigo    VARCHAR(11)  NOT NULL                   COMMENT 'Mismo valor que VentasGlobalesAccessCSV.local',
  fecha           DATE         NOT NULL                   COMMENT 'Fecha del pedido (Nicaragua)',
  hora_inicio     TIME         NOT NULL                   COMMENT 'HoraCreado Nicaragua',
  hora_fin        TIME         NOT NULL                   COMMENT 'HoraImpreso Nicaragua',
  canal_track     INT          NOT NULL                   COMMENT 'Track RTSP copiado de DVR_Sucursales.canal_caja',
  puerto_rtsp     INT          NOT NULL                   COMMENT 'Puerto VPS copiado de DVR_Sucursales.puerto_rtsp_vps',
  dvr_ip_local    VARCHAR(50)  NOT NULL                   COMMENT 'IP local del DVR (portal_ip_local)',
  dvr_usuario     VARCHAR(100) NOT NULL,
  dvr_clave       VARCHAR(255) NOT NULL,
  vps_ip          VARCHAR(50)  NOT NULL DEFAULT '198.211.97.243',
  estado          ENUM('pendiente','procesando','completado','fallido')
                               NOT NULL DEFAULT 'pendiente',
  tipo            ENUM('automatico','manual')
                               NOT NULL DEFAULT 'automatico',
  prioridad       TINYINT      NOT NULL DEFAULT 5,
  intentos        TINYINT      NOT NULL DEFAULT 0,
  error_mensaje   TEXT             DEFAULT NULL,
  -- Contexto de membresía detectado al encolar (regla de negocio)
  -- sin_membresia: CodCliente=0, evaluar si ofreció
  -- vendida:       Vendió membresía en este pedido → auto 10
  -- ya_tenia:      Cliente ya tenía membresía → null (no aplica)
  membresia_contexto ENUM('sin_membresia','vendida','ya_tenia')
                               NOT NULL DEFAULT 'sin_membresia',
  created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_estado_cola  (estado, prioridad, created_at),
  INDEX idx_cod_pedido   (cod_pedido),
  INDEX idx_local_fecha  (local_codigo, fecha),
  INDEX idx_fecha        (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Cola de videos DVR pendientes de análisis IA';


-- ────────────────────────────────────────────────────────────
-- 3. Tabla de resultados — REDISEÑO por protocolo oficial
--
-- Estructura: 5 grupos estables (columnas fijas) +
--             detalle_json flexible (breakdown por paso)
--
-- GRUPOS del Protocolo de Atención Pitaya:
--   grupo_bienvenida  → Paso 1:     Saluda con sonrisa
--   grupo_asesoria    → Pasos 2-4:  Escucha, recomienda, personaliza, acompañante
--   grupo_membresia   → Paso 5:     Solicita membresía Club Pitaya
--   grupo_cobro       → Pasos 6-8:  Pide, cobra, repite orden, propina, factura
--   (Pasos 9-10 Entrega NO se evaluan: ocurren fuera de camara de caja)
-- ────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS hikvision_analisis_ia_atencion;

CREATE TABLE hikvision_analisis_ia_atencion (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  id_cola           INT          NOT NULL                   COMMENT 'FK a hikvision_cola_analisis',
  cod_pedido        INT          NOT NULL,
  local_codigo      VARCHAR(11)  NOT NULL,
  sucursal_nombre   VARCHAR(100)     DEFAULT NULL,
  fecha             DATE         NOT NULL,
  hora_inicio       TIME         NOT NULL,
  hora_fin          TIME         NOT NULL,

  -- ── Grupos de evaluación (1-10, NULL = no observable desde esta cámara) ──
  grupo_bienvenida  TINYINT UNSIGNED DEFAULT NULL COMMENT 'Paso 1: Saludo con sonrisa y energía positiva',
  grupo_asesoria    TINYINT UNSIGNED DEFAULT NULL COMMENT 'Pasos 2-4: Escucha, recomienda, personaliza, acompañante (*opcional en fila)',
  grupo_membresia   TINYINT UNSIGNED DEFAULT NULL COMMENT 'Paso 5: Solicita y explica membresía Club Pitaya',
  grupo_cobro       TINYINT UNSIGNED DEFAULT NULL COMMENT 'Pasos 6-8: Pide nombre, indica monto, repite orden, pregunta propina, entrega factura',
  -- grupo_entrega eliminado: pasos 9-10 fuera del alcance de la camara
  cal_promedio      DECIMAL(4,2)     DEFAULT NULL COMMENT 'Promedio de grupos evaluados (no-null)',

  -- ── Detalle flexible: breakdown por cada paso individual ──────────────────
  -- Estructura JSON: ver README. Permite cambiar pasos sin modificar la tabla.
  detalle_json      JSON             DEFAULT NULL COMMENT 'Breakdown completo por paso del protocolo',

  resumen           TEXT             DEFAULT NULL,
  tiene_audio       TINYINT(1)       DEFAULT 0,
  duracion_segundos INT              DEFAULT NULL,
  modelo_ia         VARCHAR(100)     DEFAULT NULL,
  -- Contexto de membresía aplicado (heredado de la cola)
  membresia_contexto ENUM('sin_membresia','vendida','ya_tenia')
                                     DEFAULT 'sin_membresia',
  version_protocolo VARCHAR(20)      DEFAULT '1.0',
  created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_cod_pedido   (cod_pedido),
  INDEX idx_local_fecha  (local_codigo, fecha),
  INDEX idx_fecha        (fecha),
  INDEX idx_promedio     (cal_promedio),
  CONSTRAINT fk_analisis_cola
    FOREIGN KEY (id_cola) REFERENCES hikvision_cola_analisis(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Resultados de análisis de atención al cliente (Protocolo Pitaya 10 pasos)';

