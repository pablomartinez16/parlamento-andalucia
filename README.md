# Seguimiento Legislativo de España 

**Plataforma unificada de seguimiento de iniciativas legislativas con caché rápido para Congreso de Diputados y Parlamento de Andalucía.**

## 🎯 Características

- ✅ **Scraping automático** de Congreso de Diputados + Parlamento de Andalucía
- ⚡ **Caché inteligente** de resúmenes y análisis (muy rápido, sin IA pesada)
- 💾 **Base de datos SQLite** con búsqueda full-text
- 🚀 **Actualización automática** via webhook GitHub (sin intervención)
- 📊 **Dashboard responsivo** con filtros, estadísticas y posiciones de partidos
- 📋 **Posiciones de partidos** - Ve quién apoya o rechaza cada medida
- 🔒 **Bajo consumo** (~350 MB idle, ~800 MB máximo en VM 4GB)

## 📋 Estructura del Proyecto

```
seguimiento-legislativo-es/
├── app.py                      # Flask — API + servidor web
├── db.py                       # Gestión SQLite con temáticas y posiciones
├── config.py                   # Configuración centralizada
├── ia.py                       # Análisis rápido con caché (sin modelos grandes)
├── updater.py                  # Sistema auto-actualización
├── congreso_diputados_scraper.py    # Scraper Congreso (auto-detect JSON)
├── parlamento_andalucia_scraper.py  # Scraper Parlamento Andalucía
├── requirements.txt
├── install.sh                  # Instalación automática
├── parlamento.service          # Systemd service (Flask)
├── data/                       # BD y logs (generados)
├── templates/
│   ├── index.html             # Dashboard principal
│   ├── congreso.html          # Vista Congreso
│   ├── andalucia.html         # Vista Parlamento Andalucía
│   └── api_docs.html          # Documentación API
└── static/                    # CSS, JS, assets
```

## 🚀 Instalación Rápida (Ubuntu 22.04+)

```bash
# 1. Clonar repositorio
git clone https://github.com/pablomartinez16/parlamento-andalucia.git
cd parlamento-andalucia

# 2. Ejecutar instalador (instala todo, inicia servicios)
sudo bash install.sh
```

El instalador:
- Crea usuario `parlamento` (sin root)
- Instala Python 3.10+, pip, dependencias
- Crea virtualenv con todos los paquetes
- Inicializa BD, cámaras y grupos parlamentarios
- Configura servicio systemd (autostart)
- Configura cron para scrapers (3:00 UTC diario)

## 📖 Primera Ejecución

```bash
# El servicio web ya está activo en http://localhost:5000

# Para ejecutar el scraper manualmente:
sudo -u parlamento /opt/parlamento/venv/bin/python3 \
  /opt/parlamento/congreso_diputados_scraper.py

# Borrar datos y hacer scrape limpio:
rm /opt/parlamento/data/legislativo.db
sudo -u parlamento /opt/parlamento/venv/bin/python3 \
  /opt/parlamento/congreso_diputados_scraper.py
```

Tardará 5-15 minutos según cantidad de iniciativas (muy rápido, sin esperar IA).

## 🌐 Acceso a la Web

```bash
# Local (en la VM)
http://localhost:5000

# Con Tailscale (privada)
sudo tailscale up
http://parlamento.local:5000

# Con Cloudflare Tunnel (pública)
cloudflared tunnel create seguimiento
```

## 📊 API REST

### Documentación interactiva
```bash
http://localhost:5000/api
```

### Estadísticas por cámara

```bash
curl "http://localhost:5000/api/stats?camara=Congreso%20de%20Diputados"
```

Respuesta:
```json
{
  "camara": "Congreso de Diputados",
  "total": 250,
  "estados": {
    "aprobada": 85,
    "pendiente": 165
  },
  "tematicas": {
    "Sanidad": 45,
    "Educación": 38,
    "Economía": 32
  }
}
```

### Buscar iniciativas con posiciones de partidos

```bash
curl "http://localhost:5000/api/iniciativas?camara=Congreso%20de%20Diputados&pagina=1&por_pagina=10"
```

Cada iniciativa devuelve:
```json
{
  "id": 1,
  "titulo": "Reforma de la Ley Orgánica del Poder Judicial",
  "resumen": "Proposición de Ley que reforma...",
  "tematicas": ["Justicia", "Administración pública"],
  "posicion_grupos": {
    "Grupo Socialista": "A favor",
    "Grupo Popular": "En contra",
    "Podemos": "A favor",
    "Ciudadanos": "Abstención"
  }
}
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
   WEBHOOK_SECRET=tu-secreto-seguro
   GITHUB_REPO=pablomartinez16/parlamento-andalucia
   LOG_LEVEL=INFO
   ```

3. **Flujo automático:**
   - Push a `main` → Webhook automático
   - Git pull + pip install + systemctl restart
   - Logs en BD

```bash
# Ver estado de actualizaciones
curl http://localhost:5000/api/system/status
```

## 📈 Consumo de Recursos (VM 4GB)

| Componente | RAM | Notas |
|------------|-----|-------|
| Flask/Gunicorn | ~100 MB | Siempre |
| SQLite + índices | ~50 MB | Siempre |
| Caché en memoria | ~10 MB | Siempre |
| Sistema OS | ~300 MB | Ubuntu |
| **Total idle** | **~350 MB** | ✅ Muy eficiente |
| **Total scraping** | **~800 MB** | ✅ Cómodo en 4GB |

Sin modelos de IA pesados, es muy ligero.

## 📝 Configuración

Editar `config.py`:

```python
# Scraping
SCRAPER_TIMEOUT = 30
SCRAPER_DELAY = 2  # segundos entre peticiones

# Cron (formato crontab)
SCRAPER_SCHEDULE_CONGRESO = "0 3 * * *"  # 03:00 UTC diario

# Flask
FLASK_PORT = 5000
API_ITEMS_PER_PAGE = 20

# Cámaras
CAMARAS = {
    "Congreso de Diputados": {...},
    "Parlamento de Andalucía": {...}
}
```

## 🛠️ Comandos Útiles

```bash
# Ver estado del servicio web
sudo systemctl status parlamento

# Ver logs web en tiempo real
sudo journalctl -u parlamento -f

# Ver logs del scraper
tail -f /opt/parlamento/scraper.log

# Ejecutar scraper manualmente
sudo -u parlamento /opt/parlamento/venv/bin/python3 \
  /opt/parlamento/congreso_diputados_scraper.py

# Reiniciar después de cambios
sudo systemctl restart parlamento

# Ver iniciativas en BD
sqlite3 /opt/parlamento/data/legislativo.db \
  "SELECT COUNT(*) FROM iniciativas;"

# Ver posiciones de partidos
sqlite3 /opt/parlamento/data/legislativo.db \
  "SELECT g.nombre, COUNT(*) FROM posiciones p \
   JOIN grupos g ON p.grupo_id = g.id GROUP BY g.nombre;"
```

## 🔄 Cómo Funciona el Caché Rápido

1. **Primera ejecución:** Se analiza el título + tipo → genera resumen simple + temáticas
2. **Siguientes ejecuciones:** Si el título ya se vio, devuelve del caché inmediatamente
3. **Posiciones de partidos:** Se asignan por defecto (Desconocido) - se pueden actualizar manualmente

Resultado: **10-20x más rápido** que con IA pesada.

## 📞 Troubleshooting

**"Base de datos no existe"**
```bash
# Recrearla
rm /opt/parlamento/data/legislativo.db
python3 -c "import db; db.init_db(); db.cargar_camaras_defecto()"
```

**"Grupos no aparecen en API"**
```bash
# Verificar que existen
sqlite3 /opt/parlamento/data/legislativo.db \
  "SELECT COUNT(*) FROM grupos;"

# Si es 0, cargar defecto
python3 -c "import db; db.cargar_camaras_defecto()"
```

**Scraper muy lento**
- Reducir `SCRAPER_DELAY` en `config.py` (por defecto 2s)
- Reducir `API_ITEMS_PER_PAGE` para paginar menos

## 🔐 Seguridad

- ✅ Validación HMAC en webhooks
- ✅ Ejecución sin root
- ✅ Timeout en requests
- ✅ Sanitización de inputs
- ✅ No almacena credenciales en código

## 📚 Desarrollo

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Inicializar BD local
python3 -c "import db; db.init_db(); db.cargar_camaras_defecto()"

# Ejecutar Flask
python3 app.py
```

## 📄 Licencia

MIT License

## 🤝 Contribuir

Pull requests bienvenidos.

---

**Última actualización:** Mayo 2026  
**Versión:** 2.1.0 (Caché rápido + Posiciones de partidos)

