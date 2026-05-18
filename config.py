#!/usr/bin/env python3
"""
Configuración centralizada para la plataforma legislativa.
"""

import os
from pathlib import Path

# ─── Directorios ──────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

# ─── IA (TinyLlama) ────────────────────────────────────────
IA_MODEL = "TinyLlama-1.1B-Chat-v1.0"
IA_MODEL_PATH = MODELS_DIR / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
IA_MODEL_REPO = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
IA_MODEL_FILE = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

# Parámetros de inferencia
IA_CONTEXT_SIZE = 2048
IA_THREADS = 2
IA_TEMPERATURE = 0.2
IA_MAX_TOKENS = 512

# ─── Scraping ─────────────────────────────────────────────
SCRAPER_TIMEOUT = 30
SCRAPER_DELAY = 2  # segundos entre peticiones (cortesía)
SCRAPER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SCRAPER_RETRY_COUNT = 3
SCRAPER_RETRY_DELAY = 5

# ─── Temáticas ────────────────────────────────────────────
TEMATICAS_DISPONIBLES = [
    "Sanidad", "Educación", "Vivienda", "Economía", "Medio ambiente",
    "Infraestructuras", "Empleo", "Seguridad", "Justicia", "Agricultura",
    "Turismo", "Cultura", "Servicios sociales", "Administración pública",
    "Financiación autonómica", "Igualdad", "Agua", "Energía", "Transporte",
    "Vivienda pública", "Telecomunicaciones", "Industria", "Comercio",
    "Trabajo", "Derechos humanos", "Educación superior", "Ciencia",
]

# ─── Grupos Parlamentarios por Cámara ──────────────────────

# Congreso de Diputados
GRUPOS_CONGRESO = [
    "PSOE", "PP", "Vox", "Sumar", "ERC", "Junts", "PNV",
    "BNG", "Bildu", "UPN", "Partidos y Terr.", "Ciudadanos",
]

# Parlamento de Andalucía
GRUPOS_ANDALUCIA = [
    "PP-A", "PSOE-A", "Vox", "Por Andalucía", "Adelante Andalucía",
    "Ciudadanos", "Podemos",
]

# ─── Flask ────────────────────────────────────────────────
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = False
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

# ─── API ───────────────────────────────────────────────────
API_ITEMS_PER_PAGE = 20
API_MAX_ITEMS_PER_PAGE = 100
API_CACHE_TIMEOUT = 300  # 5 minutos

# ─── Webhook de Actualización ─────────────────────────────
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "cambiar-en-produccion")
WEBHOOK_BRANCH = "main"
WEBHOOK_TIMEOUT = 300

# ─── Cron Schedule ────────────────────────────────────────
SCRAPER_SCHEDULE_CONGRESO = "0 4 * * *"  # 04:00 UTC diarios
SCRAPER_SCHEDULE_ANDALUCIA = "0 3 * * *"  # 03:00 UTC diarios

# ─── Logging ──────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = DATA_DIR / "legislativo.log"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ─── Números de Legislatura ───────────────────────────────
LEGISLATURA_CONGRESO = "14"  # XIV Legislatura
LEGISLATURA_ANDALUCIA = "12"  # XII Legislatura

# ─── URLs Base ─────────────────────────────────────────────
URLS = {
    "congreso": {
        "base": "https://www.congreso.es",
        "search": "https://www.congreso.es/web/guest/buscador-de-iniciativas",
        "api": "https://www.congreso.es/web/portal-de-datos-abiertos",
    },
    "andalucia": {
        "base": "https://www.parlamentodeandalucia.es",
        "search": (
            "https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento"
            "/actividadparlamentaria/todaslasiniciativas/busquedaavanzada.do"
        ),
    },
}

# ─── Sistema de Actualización ─────────────────────────────
AUTO_UPDATE_ENABLED = True
AUTO_UPDATE_GITHUB_REPO = os.getenv("GITHUB_REPO", "pablomartinez16/seguimiento-legistativo-es")
AUTO_UPDATE_CHECK_INTERVAL = 3600  # cada hora

# ─── Seguridad ────────────────────────────────────────────
CSRF_ENABLED = True
SESSION_TIMEOUT = 3600
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_PERIOD = 3600  # 100 requests por hora

print(f"✓ Configuración cargada desde {__file__}")
