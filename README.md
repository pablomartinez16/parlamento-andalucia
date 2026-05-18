# Parlamento de Andalucía — Seguimiento Legislativo

Web de seguimiento legislativo con scraping real, IA local (Phi-3-mini) y sin base de datos.

## Estructura del proyecto

```
parlamento/
├── app.py                  # Flask — API + servidor web
├── scraper.py              # Extrae iniciativas del Parlamento
├── ia.py                   # IA local con llama-cpp-python
├── requirements.txt
├── install.sh              # Instalación automática
├── parlamento.service      # Systemd service
├── parlamento.local.nginx  # Config para tu Nginx reverse proxy
├── scraper.cron            # Entrada crontab
├── data/
│   ├── iniciativas.json    # Todas las iniciativas (generado)
│   └── stats.json          # Estadísticas (generado)
├── models/                 # Modelo Phi-3-mini (descarga automática)
└── templates/
    └── index.html          # Web frontend
```

## Instalación en la VM (Ubuntu 24.04) -> mediante clonación del repositorio

```bash
# 1. Clona el repositorio
git clone https://github.com/pablomartinez16/parlamento-andalucia

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
