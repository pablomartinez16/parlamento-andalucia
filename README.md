# Parlamento Abierto Andalucía 🏛️

Plataforma cívica web autohospedada para el seguimiento transparente, accesible y neutral de la actividad legislativa del **Parlamento de Andalucía**.

---

## Características Principales

- **Seguimiento Legislativo Integral**: Fichas individuales para proposiciones de ley, proyectos de ley, ILPs, mociones y decretos con URL permanente (`/iniciativa/{expediente}`).
- **Documentación Íntegra**: Enlaces directos a los PDFs oficiales del **Boletín Oficial del Parlamento de Andalucía (BOPA)** y **Diarios de Sesiones**.
- **Historial de Tramitación**: Visualización cronológica de cada paso parlamentario (admisión a trámite, enmiendas, ponencias, dictámenes y votaciones).
- **Votaciones y Mayorías**: Visualización gráfica del sentido del voto (a favor, en contra, abstención) con desglose por **grupos parlamentarios**.
- **Buscador y Filtros**: Búsqueda por texto libre, tipo de iniciativa y estado procesal con paginación optimizada.
- **Scraping Ético y Eficiente**: Rate limiting (1 req/s), cabeceras de identificación y sincronización incremental mediante feeds RSS oficiales cada 30 minutos.
- **Ligero y Accesible**: Stack FastAPI + PostgreSQL + PicoCSS (WCAG AA) + HTMX consumiendo menos de 300 MB de RAM.
- **Preparado para Producción**: Docker Compose, proxy inverso Caddy con HTTPS automático y scripts de copia de seguridad con rotación.

---

## Estructura del Repositorio

```
parlamento_andalucia/
├── docker-compose.yml           # Orquestación de BD, Web y Caddy
├── Dockerfile                   # Imagen ligera de producción con usuario no root
├── Caddyfile                    # Proxy inverso Caddy con HTTPS
├── .env.example                 # Plantilla de variables de entorno
├── app/
│   ├── config.py                # Ajustes y configuración con Pydantic
│   ├── database.py              # Conexión asíncrona a PostgreSQL
│   ├── models.py                # Modelo relacional SQLAlchemy
│   ├── schemas.py               # Esquemas de validación Pydantic
│   ├── main.py                  # Punto de entrada FastAPI y healthcheck
│   ├── routers/
│   │   ├── iniciativas.py       # Vistas de listado, búsqueda y detalle
│   │   └── votaciones.py        # Vistas de votaciones y resultados
│   ├── scrapers/
│   │   ├── base.py              # Cliente HTTP con rate-limiting ético
│   │   ├── iniciativas.py       # Parser de fichas parlamentarias
│   │   └── rss.py               # Ingestor de feeds RSS (iniciativas, leyes, BOPA)
│   ├── services/
│   │   ├── ingesta.py           # Orquestador idempotente de base de datos
│   │   ├── scheduler.py         # Planificador en segundo plano (APScheduler)
│   │   └── resumen.py           # Módulo pluggable para resúmenes LLM
│   ├── templates/               # Plantillas Jinja2 accesibles (PicoCSS)
│   └── static/                  # Recursos estáticos
├── scripts/
│   ├── initial_load.py          # Carga inicial de datos parlamentarios
│   ├── backup.sh                # Backup comprimido de PostgreSQL
│   └── restore.sh               # Restauración segura de copias
├── tests/                       # Pruebas unitarias de parsing
└── docs/
    └── DEPLOY.md                # Guía de instalación y hardening en Debian 12
```

---

## Puesta en Marcha Rápida (Entorno Local o VM)

Consulta la guía detallada paso a paso en [docs/DEPLOY.md](file:///C:/Users/pablo/.gemini/antigravity/scratch/parlamento_andalucia/docs/DEPLOY.md).

```bash
# 1. Configurar variables de entorno
cp .env.example .env

# 2. Iniciar contenedores con Docker Compose
docker compose up -d --build

# 3. Cargar lote inicial de datos legislativos
docker compose exec web python -m scripts.initial_load
```

---

## Probar la web sin IP pública (Túnel SSH)

Si tu VM está en una red local o privada sin IP pública expuesta, ejecuta desde tu equipo:
```bash
ssh -L 8080:localhost:80 usuario@<IP_DE_LA_VM>
```
Y abre en tu navegador: `http://localhost:8080`.

---

## Aviso Legal y Reutilización de Datos

Este proyecto es una iniciativa ciudadana independiente bajo la Ley 19/2013 de Transparencia y la Ley 37/2007 de Reutilización de Información del Sector Público. No representa oficialmente al Parlamento de Andalucía.
