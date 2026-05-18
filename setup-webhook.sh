#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  setup-webhook.sh — Configura el deploy automático desde GitHub
#  Uso: sudo bash setup-webhook.sh
# ══════════════════════════════════════════════════════════════════
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'; BOLD='\033[1m'
info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "Ejecuta con sudo: sudo bash setup-webhook.sh"

INSTALL_DIR="/opt/parlamento"
APP_USER="parlamento"
REPO_URL=""   # se rellena interactivamente

# ── 1. URL del repositorio ────────────────────────────────────────
echo ""
echo -e "${BOLD}¿Cuál es la URL de tu repositorio GitHub?${NC}"
echo -e "  Ejemplo: https://github.com/tu-usuario/parlamento-andalucia.git"
read -rp "  URL: " REPO_URL
[[ -z "$REPO_URL" ]] && error "URL vacía."

# ── 2. Secret para el webhook ─────────────────────────────────────
echo ""
info "Generando un secret seguro para el webhook de GitHub..."
WEBHOOK_SECRET=$(openssl rand -hex 32)
echo -e "  Secret: ${YELLOW}${WEBHOOK_SECRET}${NC}"
echo -e "  ${BOLD}Guárdalo — lo necesitarás al configurar el webhook en GitHub.${NC}"

# Guardar en el archivo de entorno del servicio
cat > /etc/parlamento.env << EOF
WEBHOOK_SECRET=${WEBHOOK_SECRET}
EOF
chmod 600 /etc/parlamento.env
ok "Secret guardado en /etc/parlamento.env"

# ── 3. Configurar git en el directorio de producción ─────────────
echo ""
info "Configurando git en $INSTALL_DIR..."

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    sudo -u "$APP_USER" git -C "$INSTALL_DIR" init
    sudo -u "$APP_USER" git -C "$INSTALL_DIR" remote add origin "$REPO_URL"
    sudo -u "$APP_USER" git -C "$INSTALL_DIR" fetch origin main
    sudo -u "$APP_USER" git -C "$INSTALL_DIR" checkout -f main
    ok "Repositorio clonado en $INSTALL_DIR"
else
    # Ya tiene .git, solo actualizar el remote por si cambió
    sudo -u "$APP_USER" git -C "$INSTALL_DIR" remote set-url origin "$REPO_URL"
    ok "Repositorio git ya existente — remote actualizado"
fi

# Asegurarse de que el usuario parlamento puede hacer pull sin contraseña
# (usando HTTPS con token, o SSH si el usuario tiene clave configurada)
info "Comprobando acceso al repositorio..."
if sudo -u "$APP_USER" git -C "$INSTALL_DIR" ls-remote origin HEAD &>/dev/null; then
    ok "Acceso al repositorio OK"
else
    warn "No se puede acceder al repositorio. Si es privado, necesitas un token."
    echo ""
    echo -e "  Para repositorios privados, configura un Personal Access Token:"
    echo -e "  ${YELLOW}sudo -u $APP_USER git -C $INSTALL_DIR config credential.helper store${NC}"
    echo -e "  Y usa la URL con token:"
    echo -e "  ${YELLOW}https://TU_TOKEN@github.com/usuario/parlamento-andalucia.git${NC}"
fi

# ── 4. Instalar el servicio webhook ──────────────────────────────
echo ""
info "Instalando servicio systemd del webhook..."
cp "$(dirname "$0")/parlamento-webhook.service" /etc/systemd/system/
# Ajustar paths
sed -i "s|/opt/parlamento|$INSTALL_DIR|g" /etc/systemd/system/parlamento-webhook.service
systemctl daemon-reload
systemctl enable parlamento-webhook
systemctl start parlamento-webhook
ok "Servicio parlamento-webhook activo en el puerto 9000"

# ── 5. Configurar Nginx para exponer el webhook ───────────────────
echo ""
info "Añadiendo ruta /webhook al bloque Nginx existente..."

NGINX_CONF="/etc/nginx/sites-available/parlamento.local"
if [[ -f "$NGINX_CONF" ]]; then
    # Insertar location /webhook si no existe ya
    if ! grep -q "location /webhook" "$NGINX_CONF"; then
        # Insertar antes del último } del bloque server
        sed -i '/^}/i\
\
    # Deploy automático desde GitHub\
    location /webhook {\
        proxy_pass http://127.0.0.1:9000/webhook;\
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;\
        proxy_set_header Content-Type $content_type;\
        proxy_read_timeout 60s;\
    }\
\
    # Health check del webhook\
    location /webhook-health {\
        proxy_pass http://127.0.0.1:9000/health;\
    }' "$NGINX_CONF"
        nginx -t && systemctl reload nginx
        ok "Nginx actualizado con la ruta /webhook"
    else
        ok "La ruta /webhook ya estaba en Nginx"
    fi
else
    warn "No se encontró $NGINX_CONF. Añade manualmente a tu Nginx:"
    cat << 'NGINX'
    location /webhook {
        proxy_pass http://127.0.0.1:9000/webhook;
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
        proxy_read_timeout 60s;
    }
NGINX
fi

# ── 6. Permisos sudo para el webhook (restart sin contraseña) ────
echo ""
info "Configurando permisos sudo para el webhook..."
cat > /etc/sudoers.d/parlamento-webhook << 'SUDOERS'
# Permite al webhook reiniciar el servicio de la web sin contraseña
root ALL=(ALL) NOPASSWD: /bin/systemctl restart parlamento
SUDOERS
chmod 440 /etc/sudoers.d/parlamento-webhook
ok "Permisos sudo configurados"

# ── Resumen ───────────────────────────────────────────────────────
IP_VM=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         Deploy automático configurado                    ║${NC}"
echo -e "${BOLD}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}║${NC}  Ahora ve a GitHub y crea el webhook:"
echo -e "${BOLD}║${NC}"
echo -e "${BOLD}║${NC}  1. Repo → Settings → Webhooks → Add webhook"
echo -e "${BOLD}║${NC}  2. Payload URL:"
echo -e "${BOLD}║${NC}     ${YELLOW}http://parlamento.local/webhook${NC}"
echo -e "${BOLD}║${NC}  3. Content type: ${YELLOW}application/json${NC}"
echo -e "${BOLD}║${NC}  4. Secret:"
echo -e "${BOLD}║${NC}     ${YELLOW}${WEBHOOK_SECRET}${NC}"
echo -e "${BOLD}║${NC}  5. Evento: ${YELLOW}Just the push event${NC}"
echo -e "${BOLD}║${NC}"
echo -e "${BOLD}╠══════════════════════════════════════════════════════════╣${NC}"
echo -e "${BOLD}║${NC}  Logs del webhook:"
echo -e "${BOLD}║${NC}  ${YELLOW}tail -f $INSTALL_DIR/webhook.log${NC}"
echo -e "${BOLD}║${NC}"
echo -e "${BOLD}║${NC}  Probar manualmente:"
echo -e "${BOLD}║${NC}  ${YELLOW}curl http://parlamento.local/webhook-health${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
