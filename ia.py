#!/usr/bin/env python3
"""
Módulo de IA local usando cacheo simple sin modelos grandes.
Genera resúmenes rápidos sin consumir recursos.
"""

import json
import logging
import re
from pathlib import Path

import config

log = logging.getLogger(__name__)

TEMATICAS_DISPONIBLES = config.TEMATICAS_DISPONIBLES
_resumen_cache = {}


def _extraer_resumen_simple(titulo: str, texto: str, tipo: str) -> str:
    """Genera un resumen simple sin IA (muy rápido)."""
    # Usar el titulo como base
    resumen = f"Iniciativa de tipo '{tipo}': {titulo[:200]}"
    
    # Limitar a 3-4 líneas
    if len(resumen) > 300:
        resumen = resumen[:300] + "..."
    
    return resumen


def _detectar_tematicas_simples(titulo: str, texto: str, tipo: str) -> list:
    """Detecta temáticas simples por palabras clave."""
    tematicas = []
    
    # Palabras clave por temática
    palabras_clave = {
        "Sanidad": ["salud", "sanitario", "médico", "enfermera", "hospital", "covid", "vacuna"],
        "Educación": ["educación", "escuela", "universidad", "estudiante", "profesor", "formación"],
        "Vivienda": ["vivienda", "casa", "hipoteca", "alquiler", "inmobiliario"],
        "Economía": ["economía", "fiscal", "impuesto", "presupuesto", "comercio", "financiero"],
        "Justicia": ["justicia", "juzgado", "ley", "penal", "civil", "magistrado"],
        "Empleo": ["empleo", "trabajo", "laboral", "desempleo", "ocupación", "funciones"],
        "Seguridad": ["seguridad", "policía", "guardia civil", "protección"],
        "Medio ambiente": ["ambiental", "ecología", "contaminación", "residuos", "sostenible"],
        "Infraestructuras": ["infraestructura", "carretera", "ferrocarril", "transporte", "puente"],
        "Administración pública": ["administración", "funcionario", "público", "procedimiento"],
    }
    
    texto_lower = (titulo + " " + texto).lower()
    
    for tema, palabras in palabras_clave.items():
        if any(palabra in texto_lower for palabra in palabras):
            if tema not in tematicas and tema in TEMATICAS_DISPONIBLES:
                tematicas.append(tema)
            if len(tematicas) >= 3:
                break
    
    # Por defecto
    if not tematicas:
        tematicas = ["Administración pública"]
    
    return tematicas[:3]


def analizar_iniciativa(titulo: str, texto: str, tipo: str, grupos_disponibles=None) -> dict:
    """
    Analiza una iniciativa sin IA (muy rápido, cachea resultados).
    Devuelve: resumen, tematicas, posicion_grupos
    """
    if grupos_disponibles is None:
        grupos_disponibles = config.GRUPOS_ANDALUCIA
    
    # Crear clave de cache (basada en hash del titulo)
    cache_key = hash(titulo) % (10 ** 9)
    
    # Checkear cache
    if cache_key in _resumen_cache:
        return _resumen_cache[cache_key]
    
    # Generar resumen simple y rápido
    resumen = _extraer_resumen_simple(titulo, texto, tipo)
    tematicas = _detectar_tematicas_simples(titulo, texto, tipo)
    
    # Posiciones por defecto (sin IA)
    posicion_grupos = {grupo: "Desconocido" for grupo in grupos_disponibles}
    
    resultado = {
        "resumen": resumen,
        "tematicas": tematicas,
        "posicion_grupos": posicion_grupos,
    }
    
    # Cachear
    _resumen_cache[cache_key] = resultado
    
    return resultado

