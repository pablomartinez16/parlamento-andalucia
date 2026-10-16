# Guía Completa de Despliegue y Hardening en Debian 12 (Solo Terminal)

Esta guía documenta paso a paso cómo preparar tu máquina virtual con Debian 12 (sin entorno gráfico), securizarla por SSH, instalar Docker y desplegar la plataforma **Parlamento Abierto Andalucía**.

---

## 1. Conexión SSH y Diagnóstico Inicial

Conéctate desde tu máquina anfitriona por SSH:
```bash
ssh usuario@<IP_VM_DEBIAN>
```

Comprueba los recursos y la versión de Debian:
```bash
# Versión de Debian
cat /etc/os-release

# CPU y núcleos
lscpu | grep "Model name\|CPU(s):"

# Memoria RAM disponible
free -h

# Espacio en disco
df -h /

# Servicios activos y puertos actualmente a la escucha
sudo ss -tulpn
```

---

## 2. Endurecimiento Básico del Sistema (Hardening)

### 2.1 Actualización de paquetes
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl wget git vim ufw fail2ban unattended-upgrades
```

### 2.2 Configuración del Firewall (UFW)
Permite el puerto SSH antes de encender el firewall para no perder acceso:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH (puerto 22 o el puerto personalizado que uses)
sudo ufw allow 22/tcp comment 'SSH'

# NOTA PARA CLOUDFLARE TUNNEL:
# Si usas Cloudflare Tunnel (cloudflared), NO necesitas abrir los puertos 80 ni 443 al exterior,
# ya que el túnel establece una conexión de SALIDA cifrada hacia Cloudflare.
# Si prefieres permitir tráfico HTTP/HTTPS directo además del túnel:
# sudo ufw allow 80/tcp comment 'HTTP'
# sudo ufw allow 443/tcp comment 'HTTPS'

# Habilitar firewall
sudo ufw enable
sudo ufw status verbose
```

### 2.3 Protección contra fuerza bruta (Fail2ban)
```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
sudo fail2ban-client status
```

### 2.4 Actualizaciones automáticas de seguridad
```bash
sudo dpkg-reconfigure --priority=low unattended-upgrades
sudo systemctl enable unattended-upgrades
```

---

## 3. Instalación de Docker y Docker Compose en Debian 12

Instala los repositorios oficiales de Docker:
```bash
# 1. Dependencias previas
sudo apt-get install -y ca-certificates curl gnupg

# 2. Clave GPG oficial de Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 3. Repositorio oficial de Docker para Debian Bookworm
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Instalación del motor de Docker y Docker Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Permitir a tu usuario ejecutar docker sin sudo
sudo usermod -aG docker $USER
newgrp docker

# 6. Comprobar instalación
docker --version
docker compose version
```

---

## 4. Despliegue de la Aplicación

### 4.1 Clonar o subir el proyecto a la VM
```bash
mkdir -p ~/apps
cd ~/apps

# Si clonar por git o transferir con scp:
# scp -r parlamento_andalucia usuario@<IP_VM>:~/apps/
cd parlamento_andalucia
```

### 4.2 Configurar variables de entorno
```bash
cp .env.example .env
nano .env
```
> Modifica `POSTGRES_PASSWORD` con una clave segura.

### 4.3 Construir e iniciar los contenedores
```bash
docker compose up -d --build
```

### 4.4 Verificar estado de los contenedores
```bash
docker compose ps
docker compose logs -f web
```

### 4.5 Carga inicial de datos parlamentarios (Semilla inicial)
Ejecuta el script de ingesta inicial dentro del contenedor:
```bash
docker compose exec web python -m scripts.initial_load
```

---

## 5. Acceso mediante Cloudflare Tunnel (Recomendado)

Usar Cloudflare Tunnel es la solución ideal para una VM sin IP pública:
- **No necesitas abrir puertos** de entrada en el router ni en el firewall.
- Cloudflare proporciona **HTTPS / TLS automático** con sus certificados globales.
- Oculta la IP real de tu máquina y protege contra ataques DDoS.

### Opción A: Ejecutar Cloudflare Tunnel con Docker Compose (Integrado)

1. En el panel de [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) ve a **Networks** → **Tunnels** → **Create Tunnel**.
2. Dale un nombre (ej. `parlamento-andalucia`) y selecciona el método **Docker**.
3. Copia el **token** que aparece en el comando de Cloudflare (la cadena alfanumérica larga después de `--token`).
4. Pégalo en tu archivo `.env`:
   ```bash
   CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoi...tu_token_aqui...
   ```
5. En la pestaña **Public Hostnames** de Cloudflare, configura la ruta del servicio:
   - **Subdomain / Domain**: tu subdominio (ej: `parlamento.tu-dominio.com`)
   - **Type**: `HTTP`
   - **URL**: `parlamento_caddy:80` (o `parlamento_web:8000`)
6. Levanta los contenedores activando el perfil del túnel:
   ```bash
   docker compose --profile tunnel up -d
   ```

### Opción B: Ejecutar `cloudflared` como servicio nativo en Debian

Si prefieres instalar `cloudflared` directamente en el host Debian:
```bash
# Descargar e instalar el paquete oficial de Debian
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Instalar y arrancar el túnel como servicio de systemd con tu token
sudo cloudflared service install <TU_TOKEN_DE_CLOUDFLARE>

# En el panel de Cloudflare apunta el Hostname a:
# Type: HTTP  |  URL: localhost:80
```

---

## 6. Probar la web localmente con Túnel SSH (Alternativa rápida)

Si antes de configurar Cloudflare quieres verificar que todo funciona en tu navegador local:
```bash
ssh -L 8080:localhost:80 usuario@<IP_LOCAL_DE_LA_VM>
```
Y abre en tu equipo: `http://localhost:8080`.

---

## 7. Operación y Mantenimiento (Solo Terminal)

### Ver logs en tiempo real
```bash
# Logs de la aplicación web FastAPI
docker compose logs -f web

# Logs de la base de datos
docker compose logs -f db

# Logs del proxy Caddy
docker compose logs -f caddy
```

### Ejecutar una sincronización manual inmediata
```bash
docker compose exec web python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.services.ingesta import IngestaService

async def sync():
    async with AsyncSessionLocal() as s:
        svc = IngestaService(s)
        n = await svc.sync_from_rss()
        print(f'Sincronizadas {n} iniciativas desde los feeds RSS.')

asyncio.run(sync())
"
```

### Copias de seguridad automáticas (Cron)
Crea una tarea cron en la VM:
```bash
crontab -e
```
Añade la siguiente línea para hacer backup todos los días a las 03:00 AM:
```cron
0 3 * * * cd /home/usuario/apps/parlamento_andalucia && docker compose exec -T db /backups/backup.sh >> /var/log/parlamento_backup.log 2>&1
```

### Restaurar una copia de seguridad
```bash
docker compose exec -T db /backups/restore.sh /backups/parlamento_db_AAAAMMDD_HHMMSS.sql.gz
```

### Actualizar la aplicación con código nuevo
```bash
git pull
docker compose build web
docker compose up -d web
```
