#!/usr/bin/env python3
"""
Módulo de IA local usando cacheo simple sin modelos grandes.
Genera resúmenes rápidos y infiere posiciones de partidos por palabras clave.
"""

import json
import logging
import re
from pathlib import Path

import config

log = logging.getLogger(__name__)

TEMATICAS_DISPONIBLES = config.TEMATICAS_DISPONIBLES
_resumen_cache = {}

# Ideología de grupos (para inferir posiciones)
IDEOLOGIA_GRUPOS = {
    "Grupo Parlamentario Vasco (EAJ-PNV)": "nacionalista",
    "Grupo Socialista": "izquierda",
    "PSOE": "izquierda",
    "Grupo Popular": "derecha",
    "PP": "derecha",
    "Grupo Podemos": "izquierda",
    "Podemos": "izquierda",
    "Sumar": "izquierda",
    "Grupo Ciudadanos": "centro",
    "Ciudadanos": "centro",
    "Grupo VOX": "extrema derecha",
    "VOX": "extrema derecha",
}

# Palabras clave que favorecen cada ideología
PALABRAS_CLAVE_IDEOLOGIA = {
    "izquierda": {
        "favor": ["sanidad pública", "educación pública", "salario mínimo", "impuestos", "trabajadores", 
                 "derechos sociales", "protección ambiental", "vivienda pública", "igualdad"],
        "contra": ["privatización", "reducción impuestos", "desregulación", "recortes sociales"],
    },
    "derecha": {
        "favor": ["reducción impuestos", "mercado libre", "desregulación", "empresa", "competitividad",
                 "austeridad", "ley y orden", "defensa"],
        "contra": ["impuestos", "regulación", "sanidad pública", "gasto público", "sindicatos"],
    },
    "extrema derecha": {
        "favor": ["seguridad", "inmigración restrictiva", "orden", "tradición", "soberanía"],
        "contra": ["migración", "multiculturalismo", "progresismo"],
    },
    "centro": {
        "favor": ["consenso", "equilibrio", "mercado regulado", "reformas moderadas"],
        "contra": ["extremismo", "populismo"],
    },
    "nacionalista": {
        "favor": ["autonomía", "independencia", "lengua cooficial", "derechos territoriales"],
        "contra": ["centralismo", "recentralización"],
    },
}


def _extraer_resumen_simple(titulo: str, texto: str, tipo: str) -> str:
    """Genera un resumen simple sin IA (muy rápido)."""
    resumen = f"Iniciativa de tipo '{tipo}': {titulo[:200]}"
    if len(resumen) > 300:
        resumen = resumen[:300] + "..."
    return resumen


def _detectar_tematicas_simples(titulo: str, texto: str, tipo: str) -> list:
    """Detecta temáticas simples por palabras clave."""
    tematicas = []
    palabras_clave = {
        "Sanidad": ["salud", "sanitario", "médico", "enfermera", "hospital", "covid", "vacuna", "medicamento"],
        "Educación": ["educación", "escuela", "universidad", "estudiante", "profesor", "formación", "docencia"],
        "Vivienda": ["vivienda", "casa", "hipoteca", "alquiler", "inmobiliario", "hogar"],
        "Economía": ["economía", "fiscal", "impuesto", "presupuesto", "comercio", "financiero", "banco"],
        "Justicia": ["justicia", "juzgado", "ley", "penal", "civil", "magistrado", "legal"],
        "Empleo": ["empleo", "trabajo", "laboral", "desempleo", "ocupación", "trabajador"],
        "Seguridad": ["seguridad", "policía", "guardia civil", "protección", "orden"],
        "Medio ambiente": ["ambiental", "ecología", "contaminación", "residuos", "sostenible", "clima"],
        "Infraestructuras": ["infraestructura", "carretera", "ferrocarril", "transporte", "puente", "red"],
        "Administración pública": ["administración", "funcionario", "público", "procedimiento", "gestión"],
    }
    
    texto_lower = (titulo + " " + texto).lower()
    for tema, palabras in palabras_clave.items():
        if any(palabra in texto_lower for palabra in palabras):
            if tema not in tematicas and tema in TEMATICAS_DISPONIBLES:
                tematicas.append(tema)
            if len(tematicas) >= 3:
                break
    
    if not tematicas:
        tematicas = ["Administración pública"]
    
    return tematicas[:3]


def _inferir_posicion_por_ideologia(titulo: str, texto: str, ideologia: str) -> str:
    """
    Infiere la posición de un grupo basándose en su ideología y palabras clave.
    Retorna: "A favor", "En contra", "Abstención", o "Desconocido"
    """
    if not ideologia:
        return "Desconocido"
    
    texto_lower = (titulo + " " + texto).lower()
    
    # Obtener palabras clave para esta ideología
    keywords = PALABRAS_CLAVE_IDEOLOGIA.get(ideologia, {})
    if not keywords:
        return "Desconocido"
    
    # Contar coincidencias
    favor_count = sum(1 for palabra in keywords.get("favor", []) if palabra in texto_lower)
    contra_count = sum(1 for palabra in keywords.get("contra", []) if palabra in texto_lower)
    
    # Decidir posición
    if favor_count > contra_count and favor_count > 0:
        return "A favor"
    elif contra_count > favor_count and contra_count > 0:
        return "En contra"
    elif favor_count > 0 or contra_count > 0:
        return "Abstención"  # Ambiguo
    else:
        return "Desconocido"


def analizar_iniciativa(titulo: str, texto: str, tipo: str, grupos_disponibles=None) -> dict:
    """
    Analiza una iniciativa sin IA (muy rápido, cachea resultados).
    Infiere posiciones de partidos por palabras clave + ideología.
    Devuelve: resumen, tematicas, posicion_grupos
    """
    if grupos_disponibles is None:
        grupos_disponibles = config.GRUPOS_CONGRESO
    
    # Crear clave de cache (basada en hash del titulo)
    cache_key = hash(titulo) % (10 ** 9)
    
    # Checkear cache
    if cache_key in _resumen_cache:
        return _resumen_cache[cache_key]
    
    # Generar resumen simple y rápido
    resumen = _extraer_resumen_simple(titulo, texto, tipo)
    tematicas = _detectar_tematicas_simples(titulo, texto, tipo)
    
    # Posiciones por ideología + palabras clave
    posicion_grupos = {}
    for grupo in grupos_disponibles:
        ideologia = IDEOLOGIA_GRUPOS.get(grupo, None)
        posicion = _inferir_posicion_por_ideologia(titulo, texto, ideologia)
        posicion_grupos[grupo] = posicion
    
    resultado = {
        "resumen": resumen,
        "tematicas": tematicas,
        "posicion_grupos": posicion_grupos,
    }
    
    # Cachear
    _resumen_cache[cache_key] = resultado
    
    return resultado


