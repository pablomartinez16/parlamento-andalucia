# Seguimiento Legislativo de España 

**Plataforma unificada de seguimiento de iniciativas legislativas con IA local en Congreso de Diputados y Parlamento de Andalucía.**

## 🎯 Características

- ✅ **Scraping automático** de Congreso de Diputados + Parlamento de Andalucía
- 🤖 **IA local** (TinyLlama 1.1B) para análisis y resúmenes inteligentes
- 💾 **Base de datos SQLite** con búsqueda full-text
- 🚀 **Actualización automática** via webhook GitHub (sin intervención)
- 📊 **Dashboard responsivo** con filtros y estadísticas
- 🔒 **Bajo consumo** (~450 MB idle, 3.5 GB pico en VM 4GB)

## 📋 Estructura del Proyecto

```
seguimiento-legislativo-es/
├── app.py                      # Flask — API + servidor web
├── db.py                       # Gestión SQLite
├── config.py                   # Configuración centralizada
├── ia.py                       # IA local con TinyLlama
├── updater.py                  # Sistema auto-actualización
├── parlamento_andalucia_scraper.py  # Scraper Parlamento Andalucía
├── congreso_diputados_scraper.py    # Scraper Congreso de Diputados
├── requirements.txt
├── install.sh                  # Instalación automática
├── parlamento.service          # Systemd service (Flask)
├── scraper.cron               # Entrada crontab para scrapers
├── data/                      # BD y logs (generados)
├── models/                    # Modelos IA (descarga automática)
├── templates/
│   ├── index.html             # Dashboard principal
│   ├── congreso.html          # Vista Congreso
│   └── andalucia.html         # Vista Parlamento Andalucía
└── static/                    # CSS, JS, assets
```

## 🚀 Instalación Rápida (Ubuntu 22.04+)

```bash
# 1. Clonar repositorio
git clone https://github.com/pablomartinez16/seguimiento-legislativo-es.git
cd seguimiento-legislativo-es

# 2. Ejecutar instalador
sudo bash install.sh
```

El instalador:
- Crea usuario `parlamento` (sin root)
- Instala Python 3.10+, pip, dependencias del sistema
- Crea virtualenv e instala paquetes Python
- Configura servicio systemd (autostart en reinicio)
- Configura cron para scrapers (3:00 y 4:00 UTC)

## 📖 Primera Ejecución

```bash
# Descargar modelo TinyLlama (~700 MB) y ejecutar scraper:
sudo -u parlamento /opt/seguimiento-legislativo/venv/bin/python \
  /opt/seguimiento-legislativo/parlamento_andalucia_scraper.py

sudo -u parlamento /opt/seguimiento-legislativo/venv/bin/python \
  /opt/seguimiento-legislativo/congreso_diputados_scraper.py
```

Tardará 15-30 minutos la primera vez (descarga modelo + scraping + análisis IA).

## 🌐 Acceso a la Web

```bash
# Local
http://localhost:5000

# Con Tailscale (privada)
sudo tailscale up
http://parlamento.local:5000

# Con Cloudflare Tunnel (pública)
cloudflared tunnel create seguimiento-legislativo
# Configurar CNAME en tu dominio
```

## 📊 API REST

### Estadísticas por cámara

```bash
curl "http://localhost:5000/api/stats?camara=Congreso%20de%20Diputados"
curl "http://localhost:5000/api/stats?camara=Parlamento%20de%20Andaluc%C3%ADa"
```

Respuesta:
```json
{
  "camara": "Congreso de Diputados",
  "total": 1250,
  "aprobada": 340,
  "rechazada": 180,
  "pendiente": 730,
  "tematicas": {
    "Economía": 245,
    "Sanidad": 189,
    ...
  }
}
```

### Buscar iniciativas

```bash
# Filtros: camara, tipo, estado, tema, q (búsqueda), pagina, por_pagina
curl "http://localhost:5000/api/iniciativas?camara=Congreso%20de%20Diputados&estado=aprobada&por_pagina=5"
```

### Temáticas disponibles

```bash
curl "http://localhost:5000/api/tematicas?camara=Congreso%20de%20Diputados"
```

## ⚙️ Actualización Automática (Webhook)

1. **Configurar webhook GitHub:**
   - Repo Settings → Webhooks → Add webhook
   - Payload URL: `https://tundominio.com/webhook/update`
   - Content type: `application/json`
   - Secret: Variable de entorno `WEBHOOK_SECRET`
   - Events: Push events

2. **Variables de entorno (.env o systemd):**
   ```
   WEBHOOK_SECRET=tu-secreto-super-seguro
   GITHUB_REPO=usuario/seguimiento-legislativo-es
   LOG_LEVEL=INFO
   ```

3. **Flujo automático:**
   - Push a `main` → GitHub webhook
   - `POST /webhook/update`
   - Git pull automático
   - pip install (si cambió requirements.txt)
   - systemctl restart parlamento
   - Logs en BD

**Ver estado de actualizaciones:**
```bash
curl http://localhost:5000/api/system/status
```

## 📈 Consumo de Recursos (VM 4GB)

| Componente | RAM | Notas |
|------------|-----|-------|
| Flask/Gunicorn | ~100 MB | Siempre |
| TinyLlama (idle) | ~400 MB | Entre scrapers |
| TinyLlama (scraping) | ~700 MB | Solo 3:00-4:30 UTC |
| SQLite + índices | ~50 MB | Siempre |
| Sistema OS | ~300 MB | Ubuntu |
| **Total idle** | **~850 MB** | ✅ Seguro en 4GB |
| **Total pico** | **~3.5 GB** | ✅ Cómodo en 4GB |

## 📝 Configuración

Editar `config.py`:

```python
# IA
IA_MODEL = "TinyLlama-1.1B-Chat-v1.0"
IA_CONTEXT_SIZE = 2048
IA_TEMPERATURE = 0.2

# Scraping
SCRAPER_TIMEOUT = 30
SCRAPER_DELAY = 2  # segundos entre peticiones
SCRAPER_RETRY_COUNT = 3

# Cron (formato crontab)
SCRAPER_SCHEDULE_CONGRESO = "0 4 * * *"  # 04:00 UTC
SCRAPER_SCHEDULE_ANDALUCIA = "0 3 * * *"  # 03:00 UTC

# Flask
FLASK_PORT = 5000
API_ITEMS_PER_PAGE = 20
```

## 🛠️ Comandos Útiles

```bash
# Ver estado del servicio web
sudo systemctl status parlamento

# Ver logs web en tiempo real
sudo journalctl -u parlamento -f

# Ver logs del scraper
tail -f /opt/seguimiento-legislativo/data/legislativo.log

# Ejecutar scraper manualmente
sudo -u parlamento /opt/seguimiento-legislativo/venv/bin/python \
  /opt/seguimiento-legislativo/parlamento_andalucia_scraper.py

# Reiniciar después de cambios
sudo systemctl restart parlamento

# Ver actualizaciones automáticas
sqlite3 /opt/seguimiento-legislativo/data/legislativo.db \
  "SELECT * FROM update_log ORDER BY timestamp DESC LIMIT 10;"
```

## 🔄 Migración desde parlamento-andalucia (anterior)

Si usabas la anterior versión con JSON:

```bash
# Backup de antiguo repositorio
cp -r ~/parlamento-andalucia ~/parlamento-andalucia.backup

# Clonar nuevo repo
git clone https://github.com/pablomartinez16/seguimiento-legislativo-es.git

# La BD SQLite se generará automáticamente en la primera ejecución
# Los datos antiguos (JSON) no se importan automáticamente
```

## 📞 Troubleshooting

**"Cámara no encontrada"**
```bash
# Verificar cámaras en BD
sqlite3 /opt/seguimiento-legislativo/data/legislativo.db \
  "SELECT * FROM camaras;"
```

**Modelo TinyLlama no descarga**
```bash
# Descargar manualmente
pip install llama-cpp-python
python -c "import ia; ia._get_llm()"

# El modelo se guardará en: models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf (~700 MB)
```

**Error de sintaxis después de webhook**
```bash
# Ver log de actualización
curl http://localhost:5000/api/system/status | jq '.ultimas_actualizaciones'

# Si hay error, rollback manual
cd /opt/seguimiento-legislativo
git log --oneline | head -5
git revert <commit-hash>
```

## 🔐 Seguridad

- ✅ Validación HMAC en webhooks
- ✅ Ejecución sin root (usuario `parlamento`)
- ✅ Timeout en requests (30 seg)
- ✅ Sanitización de inputs en API
- ✅ No almacena credenciales en código

**Recomendaciones:**
- Usar Cloudflare Tunnel para acceso público
- Cambiar `WEBHOOK_SECRET` en producción
- Restringir firewall a IPs de GitHub
- Usar HTTPS siempre
- Backup automático de BD (cron)

## 📚 Desarrollo

```bash
# Instalar en modo desarrollo
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Ejecutar tests (si los hay)
pytest

# Formato de código
black *.py

# Verificar sintaxis
python -m py_compile *.py
```

## 📄 Licencia

MIT License — Libre para uso personal, educativo y comercial.

## 🤝 Contribuir

Pull requests bienvenidos. Para cambios importantes, abre un issue primero.

## 📞 Contacto

- Issues: [GitHub Issues](https://github.com/pablomartinez16/seguimiento-legislativo-es/issues)
- Email: pablo@ejemplo.es (reemplazar)

---

**Última actualización:** Mayo 2026  
**Versión:** 2.0.0 (Refactor SQLite + TinyLlama + Auto-update)

# 2. Ejecuta el instalador (en la VM)
cd /parlamento-andalucia
sudo bash install.sh
```

El instalador:
- Crea el usuario `parlamento`
- Instala Python, dependencias y llama-cpp-python
- Configura el servicio systemd (autostart)
- Configura el cron diario a las 03:00
- Instala y activa Tailscale

## Primera ejecución del scraper

```bash
# Descarga el modelo (~1.8 GB, solo la primera vez) y procesa iniciativas:
sudo -u parlamento /opt/parlamento/venv/bin/python /opt/parlamento/scraper.py
```

Tardará 10-30 minutos la primera vez (descarga del modelo + scraping + análisis IA).

## Acceso con Tailscale

```bash
# En la VM del proyecto:
sudo tailscale up
```

Desde cualquier dispositivo con Tailscale activo puedes acceder
a `http://parlamento.local:5000` o a la IP Tailscale de tu Nginx.

## Consumo de recursos (4 GB RAM)

| Componente          | RAM           |
|---------------------|---------------|
| Flask / Gunicorn    | ~80 MB        |
| Phi-3-mini (en uso) | ~1.8 GB       |
| Scraper Python      | ~150 MB       |
| Tailscale           | ~50 MB        |
| Sistema operativo   | ~400 MB       |
| **Total pico**      | **~2.5 GB**   |

> El modelo IA solo se carga cuando corre el scraper (03:00).
> El resto del día Flask usa <100 MB.

## Comandos útiles

```bash
# Ver estado del servicio web
sudo systemctl status parlamento

# Ver logs web en tiempo real
sudo journalctl -u parlamento -f

# Ver logs del scraper
tail -f /opt/parlamento/scraper.log

# Ejecutar scraper manualmente
sudo -u parlamento /opt/parlamento/venv/bin/python /opt/parlamento/scraper.py

# Reiniciar web tras cambios
sudo systemctl restart parlamento
```

## Notas importantes

- El número de legislatura en `scraper.py` (`legislatura = "12"`) debe
  actualizarse al inicio de la X Legislatura cuando el Parlamento
  publique el nuevo identificador en su web.
- Los selectores CSS del scraper pueden necesitar ajuste si el Parlamento
  rediseña su web. Ver comentarios en `scraper.py`.
- Los datos de votación detallada por diputado no están disponibles en
  formato estructurado en la web oficial; se extrae el total agregado.
