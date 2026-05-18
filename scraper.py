#!/usr/bin/env python3
"""
Scraper del Parlamento de Andalucía.
Extrae iniciativas del buscador oficial y las enriquece con IA local.
"""

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from ia import analizar_iniciativa

# ── Configuración ────────────────────────────────────────────────
BASE_URL = "https://www.parlamentodeandalucia.es"
SEARCH_URL = (
    BASE_URL
    + "/webdinamica/portal-web-parlamento/actividadparlamentaria"
    "/todaslasiniciativas/busquedaavanzada.do"
)
DATA_DIR   = Path(__file__).parent / "data"
INIC_FILE  = DATA_DIR / "iniciativas.json"
STATS_FILE = DATA_DIR / "stats.json"

# Tipos a rastrear
TIPOS = [
    "Proposición de Ley",
    "Proyecto de Ley",
    "Proposición no de Ley",
    "Moción",
    "Decreto-ley",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(Path(__file__).parent / "scraper.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── JSON atómico ─────────────────────────────────────────────────
def cargar_json(path: Path, defecto):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return defecto


def guardar_json(path: Path, datos) -> None:
    """Escribe en temporal y renombra (nunca deja un JSON a medias)."""
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    tmp.replace(path)
    log.info("Guardado: %s", path.name)


def calcular_stats(iniciativas: list) -> dict:
    contadores = {"aprobada": 0, "rechazada": 0, "pendiente": 0, "retirada": 0}
    tematicas  = {}
    for ini in iniciativas:
        e = ini.get("estado", "pendiente")
        if e in contadores:
            contadores[e] += 1
        for t in ini.get("tematicas", []):
            tematicas[t] = tematicas.get(t, 0) + 1
    top_tematicas = dict(
        sorted(tematicas.items(), key=lambda x: x[1], reverse=True)[:10]
    )
    return {
        "total": len(iniciativas),
        **contadores,
        "tematicas": top_tematicas,
        "ultima_actualizacion": datetime.now().isoformat(),
    }


# ── Scraping ─────────────────────────────────────────────────────
def scrape_listado(tipo: str, pagina: int = 1) -> list:
    """Devuelve [{num, titulo, url}] de una página de resultados."""
    params = {
        "tipoIniciativa": tipo,
        "legislatura": "12",   # ← actualizar al número de la X Legislatura
        "pagina": pagina,
    }
    try:
        r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        log.warning("Error listado (%s p.%s): %s", tipo, pagina, e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    items = []

    for fila in soup.select(
        "table.tabla-iniciativas tbody tr, ul.listado-iniciativas li"
    ):
        a = fila.select_one("a")
        if not a:
            continue
        titulo = a.get_text(strip=True)
        href   = a.get("href", "")
        if not href or not titulo:
            continue
        url = href if href.startswith("http") else BASE_URL + href
        num_tag = fila.select_one(
            ".numero-expediente, .num-exp, td:first-child"
        )
        num = num_tag.get_text(strip=True) if num_tag else ""
        items.append({"num": num, "titulo": titulo, "url": url})

    return items


def scrape_detalle(url: str) -> dict:
    """Extrae texto completo y metadatos de una iniciativa."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        log.warning("Error detalle %s: %s", url, e)
        return {}

    soup = BeautifulSoup(r.text, "html.parser")

    # Texto principal
    texto = ""
    for sel in [
        ".contenido-iniciativa", ".texto-iniciativa",
        "article", "main", ".detalle-iniciativa",
    ]:
        bloque = soup.select_one(sel)
        if bloque:
            texto = bloque.get_text(separator="\n", strip=True)
            break
    if not texto:
        texto = soup.get_text(separator="\n", strip=True)[:4000]

    # Estado
    estado = "pendiente"
    for tag in soup.select(".estado, .situacion, .estado-tramitacion"):
        txt = tag.get_text(strip=True).lower()
        if "aprobad" in txt:
            estado = "aprobada"
        elif "rechazad" in txt or "denegad" in txt:
            estado = "rechazada"
        elif "retirad" in txt:
            estado = "retirada"

    # Fecha
    fecha = ""
    for tag in soup.select(".fecha, time, .fecha-presentacion"):
        fecha = tag.get_text(strip=True)
        if fecha:
            break

    # Grupo parlamentario / autor
    grupo = ""
    for tag in soup.select(
        ".grupo-parlamentario, .autor, .proponente"
    ):
        grupo = tag.get_text(strip=True)
        if grupo:
            break

    # Votación (3 números consecutivos: favor, contra, abstención)
    votos = {"favor": 0, "contra": 0, "abstencion": 0}
    for tag in soup.select(".votacion, .resultado-votacion"):
        nums = re.findall(r"\d+", tag.get_text())
        if len(nums) >= 3:
            votos = {
                "favor":      int(nums[0]),
                "contra":     int(nums[1]),
                "abstencion": int(nums[2]),
            }
            break

    return {
        "texto_completo": texto[:6000],
        "estado":         estado,
        "fecha":          fecha,
        "grupo":          grupo,
        "votos":          votos,
    }


# ── Main ─────────────────────────────────────────────────────────
def main():
    log.info("=== Scraper iniciado ===")
    DATA_DIR.mkdir(exist_ok=True)

    existentes    = cargar_json(INIC_FILE, [])
    urls_ya_vistas = {ini["url"] for ini in existentes}
    nuevas        = []

    for tipo in TIPOS:
        log.info("Tipo: %s", tipo)
        for pagina in range(1, 6):          # hasta 5 páginas por tipo
            items = scrape_listado(tipo, pagina)
            if not items:
                break

            for item in items:
                if item["url"] in urls_ya_vistas:
                    continue

                log.info("  Nueva: %s", item["titulo"][:70])
                detalle = scrape_detalle(item["url"])
                if not detalle:
                    continue

                log.info("  Analizando con IA...")
                analisis = analizar_iniciativa(
                    titulo=item["titulo"],
                    texto=detalle.get("texto_completo", ""),
                    tipo=tipo,
                )

                nuevas.append({
                    "id":             len(existentes) + len(nuevas) + 1,
                    "num":            item["num"],
                    "tipo":           tipo,
                    "titulo":         item["titulo"],
                    "url":            item["url"],
                    "grupo":          detalle.get("grupo", ""),
                    "estado":         detalle.get("estado", "pendiente"),
                    "fecha":          detalle.get("fecha", ""),
                    "votos":          detalle.get("votos", {"favor": 0, "contra": 0, "abstencion": 0}),
                    "resumen":        analisis.get("resumen", ""),
                    "tematicas":      analisis.get("tematicas", []),
                    "posicion_grupos": analisis.get("posicion_grupos", {}),
                    "fecha_scraping": datetime.now().isoformat(),
                })
                urls_ya_vistas.add(item["url"])
                time.sleep(2)           # cortesía al servidor

            time.sleep(1)

    todas = existentes + nuevas
    guardar_json(INIC_FILE, todas)
    guardar_json(STATS_FILE, calcular_stats(todas))

    log.info(
        "Nuevas: %d | Total: %d | Scraper finalizado",
        len(nuevas), len(todas),
    )


if __name__ == "__main__":
    main()
