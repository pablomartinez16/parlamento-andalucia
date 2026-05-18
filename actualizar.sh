#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  actualizar.sh — Actualización rápida del chiringuito
# ══════════════════════════════════════════════════════════════════
set -euo pipefail

# Comprobamos que eres el jefe
[[ $EUID -ne 0 ]] && { echo -e "\033[0;31m[ERROR]\033[0m Ejecuta con sudo, chacho: sudo bash actualizar.sh"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/opt/parlamento"
APP_USER="parlamento"

echo -e "\n\033[1;34m[1/4]\033[0m Pasando los archivos nuevecicos a producción..."
cp -r "$PROJECT_DIR"/. "$INSTALL_DIR"/

echo -e "\033[1;34m[2/4]\033[0m Dejando los permisos niquelaos..."
chown -R "$APP_USER":"$APP_USER" "$INSTALL_DIR"

echo -e "\033[1;34m[3/4]\033[0m Actualizando librerías de Python (por si las moscas)..."
sudo -u "$APP_USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q

echo -e "\033[1;34m[4/4]\033[0m Pegándole un reinicio al motor de la web..."
systemctl restart parlamento

echo -e "\n\033[0;32m[OK]\033[0m ¡Apañao! La web ya está corriendo con lo último.\n"