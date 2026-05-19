#!/usr/bin/env python3
"""
Módulo de análisis simple sin IA.
Genera resúmenes muy rápidos por palabras clave y temáticas.
"""

import logging
from pathlib import Path

import config

log = logging.getLogger(__name__)

TEMATICAS_DISPONIBLES = config.TEMATICAS_DISPONIBLES
_resumen_cache = {}


def _extraer_resumen_simple(titulo: str, tipo: str) -> str:
    """Genera un resumen simple (muy rápido)."""
    resumen = f"Iniciativa de tipo '{tipo}': {titulo[:200]}"
    if len(resumen) > 300:
        resumen = resumen[:300] + "..."
    return resumen


def _detectar_tematicas_simples(titulo: str, texto: str) -> list:
    """Detecta temáticas simples por palabras clave."""
    tematicas = []
    
    palabras_clave = {
        "Sanidad": ["salud", "sanitario", "médico", "enfermera", "hospital", "covid", "vacuna"],
        "Educación": ["educación", "escuela", "universidad", "estudiante", "profesor", "formación"],
        "Vivienda": ["vivienda", "casa", "hipoteca", "alquiler", "inmobiliario"],
        "Economía": ["economía", "fiscal", "impuesto", "presupuesto", "comercio", "financiero"],
        "Justicia": ["justicia", "juzgado", "ley", "penal", "civil", "magistrado"],
        "Empleo": ["empleo", "trabajo", "laboral", "desempleo", "ocupación"],
        "Seguridad": ["seguridad", "policía", "guardia civil", "protección"],
        "Medio ambiente": ["ambiental", "ecología", "contaminación", "residuos", "sostenible"],
        "Infraestructuras": ["infraestructura", "carretera", "ferrocarril", "transporte"],
        "Administración pública": ["administración", "funcionario", "público", "procedimiento"],
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


def analizar_iniciativa(titulo: str, texto: str, tipo: str, grupos_disponibles=None) -> dict:
    """
    Analiza una iniciativa rápidamente.
    Sin IA, sin complejidad — solo resumen, temáticas y posiciones como "Desconocido".
    """
    if grupos_disponibles is None:
        grupos_disponibles = config.GRUPOS_CONGRESO
    
    # Cache por titulo
    cache_key = hash(titulo) % (10 ** 9)
    if cache_key in _resumen_cache:
        return _resumen_cache[cache_key]
    
    # Análisis simple
    resumen = _extraer_resumen_simple(titulo, tipo)
    tematicas = _detectar_tematicas_simples(titulo, texto)
    
    # Posiciones: todas "Desconocido" (honesto, sin asumir)
    posicion_grupos = {grupo: "Desconocido" for grupo in grupos_disponibles}
    
    resultado = {
        "resumen": resumen,
        "tematicas": tematicas,
        "posicion_grupos": posicion_grupos,
    }
    
    _resumen_cache[cache_key] = resultado
    return resultado



