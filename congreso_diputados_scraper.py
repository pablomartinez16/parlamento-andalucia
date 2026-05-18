#!/usr/bin/env python3
"""
Scraper del Congreso de Diputados.
Extrae iniciativas del buscador oficial y las almacena en SQLite.
Enriquece con IA local.
"""

import logging
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import config
import db
from ia import analizar_iniciativa

log = logging.getLogger(__name__)

CAMARA_NOMBRE = "Congreso de Diputados"
BASE_URL = "https://www.congreso.es"
SEARCH_URL = "https://www.congreso.es/web/guest/buscador-de-iniciativas"

TIPOS = [
    "Proyecto de Ley",
    "Proposición de Ley",
    "Proposición no de Ley",
    "Moción",
    "Decreto-ley",
]

HEADERS = {
    "User-Agent": config.SCRAPER_USER_AGENT,
    "Accept-Language": "es-ES,es;q=0.9",
}


def scrape_listado(tipo: str, pagina: int = 1) -> list:
    """Devuelve [{num, titulo, url}] de una página de resultados."""
    params = {
        "tipo": tipo,
        "legislatura": config.LEGISLATURA_CONGRESO,
        "pageNumber": pagina,
    }
    
    for intento in range(config.SCRAPER_RETRY_COUNT):
        try:
            r = requests.get(
                SEARCH_URL,
                params=params,
                headers=HEADERS,
                timeout=config.SCRAPER_TIMEOUT,
            )
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if intento < config.SCRAPER_RETRY_COUNT - 1:
                log.warning(f"Reintentando ({intento+1}/{config.SCRAPER_RETRY_COUNT}): {e}")
                time.sleep(config.SCRAPER_RETRY_DELAY)
            else:
                log.error(f"Error listado ({tipo} p.{pagina}): {e}")
                return []

    soup = BeautifulSoup(r.text, "html.parser")
    items = []

    # Selectores para Congreso.es (pueden cambiar)
    for fila in soup.select("div.iniciativa, tr.iniciativa, div.resultado-busqueda"):
        a = fila.select_one("a")
        if not a:
            continue
        
        titulo = a.get_text(strip=True)
        href = a.get("href", "")
        
        if not href or not titulo:
            continue
        
        url = href if href.startswith("http") else BASE_URL + href
        
        # Buscar número de iniciativa
        num_tag = fila.select_one(".numero, .num-iniciativa, .expediente")
        num = num_tag.get_text(strip=True) if num_tag else ""
        
        items.append({"num": num, "titulo": titulo, "url": url})

    return items


def scrape_detalle(url: str) -> dict:
    """Extrae texto completo y metadatos de una iniciativa."""
    for intento in range(config.SCRAPER_RETRY_COUNT):
        try:
            r = requests.get(url, headers=HEADERS, timeout=config.SCRAPER_TIMEOUT)
            r.raise_for_status()
            break
        except requests.RequestException as e:
            if intento < config.SCRAPER_RETRY_COUNT - 1:
                time.sleep(config.SCRAPER_RETRY_DELAY)
            else:
                log.error(f"Error detalle {url}: {e}")
                return {}

    soup = BeautifulSoup(r.text, "html.parser")

    # Texto principal
    texto = ""
    for sel in [
        ".contenido-iniciativa",
        ".texto-iniciativa",
        ".detalle-iniciativa",
        ".contenido-principal",
        "article",
        "main",
    ]:
        bloque = soup.select_one(sel)
        if bloque:
            texto = bloque.get_text(separator="\n", strip=True)
            break
    
    if not texto:
        texto = soup.get_text(separator="\n", strip=True)[:3000]

    # Estado
    estado = "pendiente"
    for tag in soup.select(".estado, .situacion, .estado-tramitacion, .tramitacion"):
        txt = tag.get_text(strip=True).lower()
        if "aprobad" in txt:
            estado = "aprobada"
        elif "rechazad" in txt or "denegad" in txt or "caducad" in txt:
            estado = "rechazada"
        elif "retirad" in txt:
            estado = "retirada"

    # Fecha
    fecha = ""
    for tag in soup.select(".fecha, time, .fecha-presentacion, .fecha-registro"):
        fecha = tag.get_text(strip=True)
        if fecha:
            break

    # Grupo parlamentario / autor
    grupo = ""
    for tag in soup.select(".grupo-parlamentario, .autor, .proponente, .diputados"):
        txt = tag.get_text(strip=True)
        if txt and len(txt) < 100:
            grupo = txt
            break

    # Votación
    votos = {"favor": 0, "contra": 0, "abstencion": 0}
    for tag in soup.select(".votacion, .resultado-votacion, .resultado"):
        nums = re.findall(r"\d+", tag.get_text())
        if len(nums) >= 3:
            votos = {
                "favor": int(nums[0]),
                "contra": int(nums[1]),
                "abstencion": int(nums[2]),
            }
            break

    return {
        "texto_completo": texto[:5000],
        "estado": estado,
        "fecha": fecha,
        "grupo": grupo,
        "votos": votos,
    }


def scrape():
    """Ejecuta el scraping completo."""
    log.info("=== Scraper Congreso de Diputados iniciado ===")
    
    camara = db.obtener_camara(CAMARA_NOMBRE)
    if not camara:
        log.error(f"Cámara {CAMARA_NOMBRE} no encontrada en BD")
        return
    
    camara_id = camara["id"]
    nuevas = 0
    errores = 0

    for tipo in TIPOS:
        log.info(f"Tipo: {tipo}")
        for pagina in range(1, 6):
            items = scrape_listado(tipo, pagina)
            if not items:
                break

            for item in items:
                try:
                    log.info(f"  Procesando: {item['titulo'][:70]}")
                    detalle = scrape_detalle(item["url"])
                    if not detalle:
                        errores += 1
                        continue

                    log.info("    Analizando con IA...")
                    analisis = analizar_iniciativa(
                        titulo=item["titulo"],
                        texto=detalle.get("texto_completo", ""),
                        tipo=tipo,
                        grupos_disponibles=config.GRUPOS_CONGRESO,
                    )

                    ini_id = db.insertar_iniciativa(
                        camara_id=camara_id,
                        datos={
                            "numero": item["num"],
                            "tipo": tipo,
                            "titulo": item["titulo"],
                            "url": item["url"],
                            "estado": detalle.get("estado", "pendiente"),
                            "fecha_presentacion": detalle.get("fecha"),
                            "grupo_autor": detalle.get("grupo"),
                            "texto_completo": detalle.get("texto_completo"),
                            "resumen": analisis.get("resumen"),
                            "tematicas": analisis.get("tematicas", []),
                            "votos": detalle.get("votos"),
                            "posicion_grupos": analisis.get("posicion_grupos", {}),
                        },
                    )
                    
                    if ini_id:
                        nuevas += 1
                    
                    time.sleep(config.SCRAPER_DELAY)

                except Exception as e:
                    log.error(f"Error procesando {item['titulo']}: {e}")
                    errores += 1

            time.sleep(1)

    log.info(f"Scraper finalizado. Nuevas: {nuevas}, Errores: {errores}")
    db.registrar_scraper_log(camara_id, "completado", nuevas, errores)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler(),
        ],
    )
    db.init_db()
    db.cargar_camaras_defecto()
    scrape()
