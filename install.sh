#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  install.sh — Instalación automática del seguimiento legislativo
#  Probado en Ubuntu 24.04 LTS
#  Uso: sudo bash install.sh
# ══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Colores ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'; BOLD='\033[1m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
section() { echo -e "\n${BOLD}══ $* ══${NC}"; }

# ── Verificaciones previas ───────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Ejecuta con sudo: sudo bash install.sh"
[[ ! -f "$(dirname "$0")/app.py" ]] && error "Ejecuta desde el directorio del proyecto."

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/opt/parlamento"
APP_USER="parlamento"

section "1/7 Actualizando sistema"
apt-get update -qq
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    build-essential cmake git curl \
    tailscale 2>/dev/null || true
ok "Paquetes del sistema instalados"

section "2/7 Creando usuario del servicio"
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /bin/bash --create-home "$APP_USER"
    ok "Usuario '$APP_USER' creado"
else
    ok "Usuario '$APP_USER' ya existe"
fi

section "3/7 Copiando archivos del proyecto"
mkdir -p "$INSTALL_DIR"/{data,templates,static/{css,js},models}
cp -r "$PROJECT_DIR"/. "$INSTALL_DIR"/
chown -R "$APP_USER":"$APP_USER" "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"
ok "Archivos copiados en $INSTALL_DIR"

section "4/7 Creando entorno virtual Python e instalando dependencias"
info "Instalando dependencias Python..."
sudo -u "$APP_USER" python3 -m venv "$INSTALL_DIR/venv"

sudo -u "$APP_USER" bash -c "
    source $INSTALL_DIR/venv/bin/activate
    pip install --upgrade pip setuptools wheel -q
    pip install -r $INSTALL_DIR/requirements.txt -q
"
ok "Dependencias Python instaladas (sin llama-cpp-python - usando cache simple)"

section "5/7 Inicializando base de datos"
sudo -u "$APP_USER" bash -c "
    source $INSTALL_DIR/venv/bin/activate
    cd $INSTALL_DIR
    python3 -c \"
import db
db.init_db()
db.cargar_camaras_defecto()
print('✓ Base de datos inicializada')
print('✓ Cámaras cargadas')
print('✓ Grupos parlamentarios cargados')
    \"
"
ok "Base de datos lista con esquema + cámaras + grupos"

section "6/7 Configurando servicio systemd"
cp "$INSTALL_DIR/parlamento.service" /etc/systemd/system/parlamento.service
# Ajustar paths en el service
sed -i "s|/opt/parlamento|$INSTALL_DIR|g" /etc/systemd/system/parlamento.service
sed -i "s|User=parlamento|User=$APP_USER|g" /etc/systemd/system/parlamento.service

systemctl daemon-reload
systemctl enable parlamento
systemctl start parlamento
ok "Servicio 'parlamento' activo y habilitado"

section "7/7 Configurando cron del scraper"
CRON_LINE="0 3 * * * $INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/congreso_diputados_scraper.py >> $INSTALL_DIR/scraper.log 2>&1"
(crontab -u "$APP_USER" -l 2>/dev/null | grep -v "congreso_diputados_scraper.py"; echo "$CRON_LINE") \
    | crontab -u "$APP_USER" -
ok "Cron configurado (diario a las 03:00 UTC)"

# ── Resumen final ────────────────────────────────────────────────
IP_VM=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║           Instalación completada ✓                  ║${NC}"
echo -e "${BOLD}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}║${NC}  Web local:    ${GREEN}http://$IP_VM:5000${NC}"
echo -e "${BOLD}║${NC}  Datos:        ${INSTALL_DIR}/data/"
echo -e "${BOLD}║${NC}  BD:           ${INSTALL_DIR}/data/legislativo.db"
echo -e "${BOLD}║${NC}  Logs web:     ${INSTALL_DIR}/gunicorn.log"
echo -e "${BOLD}║${NC}  Logs scraper: ${INSTALL_DIR}/scraper.log"
echo -e "${BOLD}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}║${NC}  En tu Nginx (reverse proxy), añade:"
echo -e "${BOLD}║${NC}  ${YELLOW}proxy_pass http://$IP_VM:5000;${NC}"
echo -e "${BOLD}║${NC}  (usa el fichero parlamento.local.nginx de guía)"
echo -e "${BOLD}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}║${NC}  Para ejecutar el scraper ahora:"
echo -e "${BOLD}║${NC}  ${YELLOW}sudo -u $APP_USER $INSTALL_DIR/venv/bin/python3 \\${NC}"
echo -e "${BOLD}║${NC}  ${YELLOW}  $INSTALL_DIR/congreso_diputados_scraper.py${NC}"
echo -e "${BOLD}║${NC}"
echo -e "${BOLD}║${NC}  Para borrar datos y hacer scrape limpio:"
echo -e "${BOLD}║${NC}  ${YELLOW}rm $INSTALL_DIR/data/legislativo.db${NC}"
echo -e "${BOLD}║${NC}  ${YELLOW}sudo -u $APP_USER $INSTALL_DIR/venv/bin/python3 \\${NC}"
echo -e "${BOLD}║${NC}  ${YELLOW}  $INSTALL_DIR/congreso_diputados_scraper.py${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
