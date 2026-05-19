#!/usr/bin/env python3
"""
Scraper mejorado para Congreso de Diputados con detección automática de URLs.
Descarga datasets JSON desde la API pública de datos abiertos.
Se adapta automáticamente a cambios diarios sin necesidad de mantenimiento.
"""

import json
import logging
import re
import time
from pathlib import Path

import requests

import config
import db
from ia import analizar_iniciativa

log = logging.getLogger(__name__)

CAMARA_NOMBRE = "Congreso de Diputados"
OPENDATA_URL = "https://www.congreso.es/es/opendata/iniciativas"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.congreso.es/es/datos-abiertos",
}


def obtener_urls_json_dinamicamente() -> dict:
    """
    Detecta automáticamente URLs de datasets JSON desde la página de OpenData.
    Se adapta a cambios de URLs sin necesidad de actualizar el código.
    """
    try:
        log.info("Buscando datasets JSON disponibles en OpenData...")
        resp = requests.get(OPENDATA_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        
        # Buscar patrones de URLs JSON (relativas o absolutas)
        urls_json = re.findall(
            r'(?:https://www\.congreso\.es)?(/webpublica/opendata/iniciativas/[^"]+\.json)',
            resp.text
        )
        
        if not urls_json:
            log.error("❌ No se encontraron URLs JSON en la página de OpenData")
            return {}
        
        # Convertir a URLs absolutas y eliminar duplicados
        urls_completas = []
        for url in urls_json:
            # Si es relativa, construir URL absoluta
            if url.startswith('/'):
                url_completa = f"https://www.congreso.es{url}"
            else:
                url_completa = url
            urls_completas.append(url_completa)
        
        urls_unicas = list(set(urls_completas))
        log.info(f"✓ Encontrados {len(urls_unicas)} datasets JSON")
        
        datasets = {}
        for url in urls_unicas:
            filename = url.split('/')[-1].replace('.json', '')
            log.info(f"  ✓ {filename}")
            datasets[filename] = url
        
        return datasets
    except Exception as e:
        log.error(f"❌ Error obteniendo URLs: {e}")
        return {}


def descargar_json(url: str) -> list:
    """Descarga y parsea JSON desde URL con reintentos."""
    for intento in range(config.SCRAPER_RETRY_COUNT):
        try:
            log.debug(f"Descargando {url.split('/')[-1][:50]}... (intento {intento+1})")
            resp = requests.get(url, headers=HEADERS, timeout=config.SCRAPER_TIMEOUT)
            resp.raise_for_status()
            return json.loads(resp.text)
        except Exception as e:
            if intento < config.SCRAPER_RETRY_COUNT - 1:
                log.warning(f"Reintentando: {e}")
                time.sleep(2 ** intento)
            else:
                log.error(f"Error descargando {url.split('/')[-1]}: {e}")
    return []


def mapear_estado(situacion_actual: str) -> str:
    """Normaliza la situación actual a estado estándar."""
    situacion = situacion_actual.lower()
    if "cerrado" in situacion or "aprobado" in situacion:
        return "aprobada"
    elif "rechazado" in situacion:
        return "rechazada"
    else:
        return "pendiente"


def procesar_iniciativa(iniciativa: dict, camara_id: int) -> bool:
    """
    Procesa una iniciativa JSON e inserta en BD.
    Retorna True si fue exitoso.
    """
    try:
        # Extraer campos del JSON
        titulo = (
            iniciativa.get("TITULO_LEY", "") or 
            iniciativa.get("OBJETO", "")
        ).strip()
        if not titulo:
            return False
        
        # Coger el PDF de varios campos posibles
        url = (
            iniciativa.get("PDF", "") or 
            iniciativa.get("ENLACESBOCG", "") or
            ""
        )
        if not url:
            log.debug(f"  ⚠️  Sin URL de PDF: {titulo[:60]}")
            return False
        
        # Extraer número de expediente de varios campos posibles
        num_expediente = (
            iniciativa.get("NUMEXPEDIENTE", "") or 
            iniciativa.get("NUM_EXPEDIENTE", "") or
            iniciativa.get("EXPEDIENTE", "") or
            iniciativa.get("NUMERO_LEY", "") or
            ""
        )
        
        tipo = iniciativa.get("TIPO", "").split()[0] if iniciativa.get("TIPO") else ""
        estado = mapear_estado(iniciativa.get("SITUACIONACTUAL", ""))
        fecha = iniciativa.get("FECHAPRESENTACION", "")
        
        # Truncar título para BD
        titulo_db = titulo[:500]
        
        # Análisis con IA
        log.debug(f"  Analizando: {titulo_db[:60]}...")
        resultado_ia = analizar_iniciativa(
            titulo=titulo_db,
            texto=titulo_db,
            tipo=tipo,
        )
        
        # Preparar datos en formato que espera insertar_iniciativa
        datos = {
            "tipo": tipo,
            "numero": num_expediente,
            "titulo": titulo_db,
            "url": url,
            "estado": estado,
            "fecha_presentacion": fecha,
            "grupo_autor": iniciativa.get("AUTOR", ""),
            "texto_completo": titulo_db,
            "resumen": resultado_ia.get("resumen", ""),
            "tematicas": resultado_ia.get("tematicas", []),
            "posicion_grupos": resultado_ia.get("posicion_grupos", {}),
        }
        
        # Insertar en BD
        db.insertar_iniciativa(camara_id=camara_id, datos=datos)
        return True
    except Exception as e:
        log.error(f"Error procesando iniciativa: {e}")
        return False


def scrape():
    """Ejecuta el scraping completo usando API JSON."""
    log.info("=" * 80)
    log.info("=== Scraper Congreso de Diputados (Auto-detect JSON) iniciado ===")
    log.info("=" * 80)
    
    # Inicializar BD
    db.init_db()
    db.cargar_camaras_defecto()
    
    # Obtener cámara
    camara = db.obtener_camara(CAMARA_NOMBRE)
    if not camara:
        log.error(f"❌ Cámara '{CAMARA_NOMBRE}' no encontrada en BD")
        return
    
    # Obtener URLs dinámicamente (se adapta cada día automáticamente)
    datasets = obtener_urls_json_dinamicamente()
    if not datasets:
        log.error("❌ No se encontraron datasets JSON para procesar")
        return
    
    camara_id = camara["id"]
    total_nuevas = 0
    total_errores = 0
    
    # Procesar cada dataset
    for nombre, url in datasets.items():
        log.info(f"\n📥 Procesando: {nombre}")
        
        # Descargar JSON
        datos = descargar_json(url)
        if not datos:
            log.warning(f"  ⚠️  No hay datos en {nombre}")
            continue
        
        log.info(f"  ✓ {len(datos)} iniciativas encontradas")
        
        # Procesar cada iniciativa
        for iniciativa in datos:
            if procesar_iniciativa(iniciativa, camara_id):
                total_nuevas += 1
            else:
                total_errores += 1
            
            time.sleep(config.SCRAPER_DELAY)
    
    log.info("\n" + "=" * 80)
    log.info(f"✓ Scraper finalizado. Nuevas: {total_nuevas}, Errores: {total_errores}")
    log.info("=" * 80)
    
    # Registrar en BD
    db.registrar_scraper_log(camara_id, "completado", total_nuevas, total_errores)


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
