#!/bin/bash
# ============================================================
# setup_vps.sh — Configuración inicial del VPS para HikvisionAnalisisIA
# Ejecutar UNA SOLA VEZ via SSH después del primer clone/rsync
#
# Uso:
#   ssh root@198.211.97.243
#   cd /opt/hikvision-ia
#   bash scripts/setup_vps.sh
# ============================================================

set -e
PROJECT_DIR="/opt/hikvision-ia"

echo "=================================================="
echo "  HikvisionAnalisisIA — Setup inicial VPS"
echo "=================================================="

# 1. Crear directorio del proyecto si no existe
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/temp"
mkdir -p "$PROJECT_DIR/logs"
echo "✅ Directorios creados"

# 2. Instalar dependencias del sistema
echo ""
echo "📦 Instalando dependencias del sistema..."
apt-get update -qq
apt-get install -y python3 python3-venv python3-pip ffmpeg

echo "✅ ffmpeg instalado: $(ffmpeg -version 2>&1 | head -1)"

# 3. Crear entorno virtual Python DENTRO del proyecto
echo ""
echo "🐍 Creando entorno virtual Python..."
cd "$PROJECT_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip --quiet
venv/bin/pip install -r requirements.txt --quiet
echo "✅ venv creado con dependencias"

# 4. Crear .env desde el ejemplo si no existe
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo ""
    echo "⚠️  IMPORTANTE: Edita el .env con los valores reales:"
    echo "    nano $PROJECT_DIR/.env"
    echo "    (El HIK_API_TOKEN ya está en el archivo de ejemplo)"
else
    echo "✅ .env ya existe, no se sobreescribe"
fi

# 5. Registrar servicio systemd
echo ""
echo "⚙️  Configurando servicio systemd..."
cp "$PROJECT_DIR/systemd/hikvision-worker.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable hikvision-worker
echo "✅ Servicio registrado y habilitado para inicio automático"

# 6. Verificar ffmpeg
echo ""
ffmpeg -version 2>&1 | head -3
echo ""

echo "=================================================="
echo "  Setup completado. Próximos pasos:"
echo ""
echo "  1. Editar .env si no lo hiciste:"
echo "     nano $PROJECT_DIR/.env"
echo ""
echo "  2. Iniciar el worker:"
echo "     systemctl start hikvision-worker"
echo ""
echo "  3. Ver logs en tiempo real:"
echo "     journalctl -u hikvision-worker -f"
echo ""
echo "  4. Test manual (después de configurar túnel SSH):"
echo "     cd $PROJECT_DIR"
echo "     venv/bin/python scripts/test_manual.py --pedido XXXX --local 10"
echo "=================================================="
