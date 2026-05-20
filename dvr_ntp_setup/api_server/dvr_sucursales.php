<?php
/**
 * dvr_sucursales.php — Endpoint API para consulta de DVRs Hikvision
 * 
 * Ruta: api.batidospitaya.com/api/hikvision/dvr_sucursales.php
 * 
 * Parámetros GET opcionales:
 *   tunel_activo=1     → solo DVRs con túnel activo
 *   cod_sucursal=N     → un DVR específico por código
 * 
 * Autenticación: Header X-WSP-Token (igual que todos los endpoints de esta API)
 * 
 * Respuesta JSON:
 * {
 *   "success": true,
 *   "dvrs": [ { ... }, ... ]
 * }
 */

require_once __DIR__ . '/../_auth.php';   // valida X-WSP-Token
require_once __DIR__ . '/../_db.php';     // $pdo — conexión a la BD


header('Content-Type: application/json; charset=utf-8');

// ── Construcción de la query ──────────────────────────────────
$where = [];
$params = [];

if (isset($_GET['tunel_activo'])) {
    $where[] = 'tunel_activo = :tunel_activo';
    $params[':tunel_activo'] = (int) $_GET['tunel_activo'];
}

if (isset($_GET['cod_sucursal'])) {
    $where[] = 'cod_sucursal = :cod_sucursal';
    $params[':cod_sucursal'] = (int) $_GET['cod_sucursal'];
}

$sql = "
    SELECT
        cod_sucursal,
        nombre_sucursal,
        modelo,
        marca,
        serial,
        portal_ip_local,
        portal_usuario,
        portal_clave,
        puerto_rtsp_vps,
        tunel_activo,
        puerto_http_vps
    FROM DVR_Sucursales
" . ($where ? ('WHERE ' . implode(' AND ', $where)) : '') . "
    ORDER BY nombre_sucursal ASC
";

try {
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $dvrs = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // Normalizar tipos numéricos
    foreach ($dvrs as &$dvr) {
        $dvr['cod_sucursal'] = (int) $dvr['cod_sucursal'];
        $dvr['puerto_rtsp_vps'] = $dvr['puerto_rtsp_vps'] !== null ? (int) $dvr['puerto_rtsp_vps'] : null;
        $dvr['tunel_activo'] = (bool) $dvr['tunel_activo'];
        $dvr['puerto_http_vps'] = $dvr['puerto_http_vps'] !== null ? (int) $dvr['puerto_http_vps'] : null;
    }

    echo json_encode([
        'success' => true,
        'dvrs' => $dvrs,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Error de base de datos',
    ]);
}
