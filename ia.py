#!/usr/bin/env python3
"""
Módulo de IA local usando llama-cpp-python con Phi-3-mini Q4.
Carga el modelo una sola vez por ejecución del scraper.
Con 4 GB RAM: el modelo ocupa ~1.8 GB, deja margen suficiente.
"""

import json
import logging
import os
import re
from pathlib import Path
from functools import lru_cache

log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "models" / "Phi-3-mini-4k-instruct-Q4_K_M.gguf"
MODEL_REPO = "microsoft/Phi-3-mini-4k-instruct-gguf"
MODEL_FILE = "Phi-3-mini-4k-instruct-q4.gguf"

TEMATICAS_DISPONIBLES = [
    "Sanidad", "Educación", "Vivienda", "Economía", "Medio ambiente",
    "Infraestructuras", "Empleo", "Seguridad", "Justicia", "Agricultura",
    "Turismo", "Cultura", "Servicios sociales", "Administración pública",
    "Financiación autonómica", "Igualdad", "Agua", "Energía", "Transporte",
]

GRUPOS = [
    "PP-A", "PSOE-A", "Vox", "Por Andalucía", "Adelante Andalucía",
]

_llm = None


def _get_llm():
    """Carga el modelo una sola vez (singleton)."""
    global _llm
    if _llm is not None:
        return _llm

    try:
        from llama_cpp import Llama
    except ImportError:
        log.error("llama-cpp-python no instalado. Ejecuta: pip install llama-cpp-python")
        return None

    if not MODEL_PATH.exists():
        log.info("Descargando modelo %s...", MODEL_FILE)
        try:
            _llm = Llama.from_pretrained(
                repo_id=MODEL_REPO,
                filename=MODEL_FILE,
                cache_dir=str(MODEL_PATH.parent),
                n_ctx=4096,
                n_threads=2,
                verbose=False,
            )
            log.info("Modelo cargado desde HuggingFace.")
        except Exception as e:
            log.error("Error al descargar modelo: %s", e)
            return None
    else:
        try:
            _llm = Llama(
                model_path=str(MODEL_PATH),
                n_ctx=4096,
                n_threads=2,
                verbose=False,
            )
            log.info("Modelo cargado desde disco.")
        except Exception as e:
            log.error("Error al cargar modelo: %s", e)
            return None

    return _llm


def _llamar_ia(prompt: str, max_tokens: int = 512) -> str:
    """Llama al modelo y devuelve el texto generado."""
    llm = _get_llm()
    if llm is None:
        return ""
    try:
        respuesta = llm.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente experto en derecho parlamentario español "
                        "y en el funcionamiento del Parlamento de Andalucía. "
                        "Respondes siempre en español, de forma clara y concisa. "
                        "Cuando se te pide JSON, devuelves ÚNICAMENTE el JSON, "
                        "sin texto adicional ni bloques de código."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return respuesta["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error("Error en inferencia IA: %s", e)
        return ""


def _extraer_json(texto: str) -> dict:
    """Extrae el primer objeto JSON válido de un texto."""
    # Eliminar bloques markdown si los hay
    texto = re.sub(r"```(?:json)?\s*", "", texto).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        # Intentar extraer el objeto JSON con regex
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def analizar_iniciativa(titulo: str, texto: str, tipo: str) -> dict:
    """
    Analiza una iniciativa parlamentaria y devuelve:
    - resumen: 3-4 líneas en lenguaje claro
    - tematicas: lista de temas relevantes
    - posicion_grupos: posición estimada de cada grupo parlamentario
    """
    # Recortar texto para no exceder el contexto
    texto_recortado = texto[:3000] if len(texto) > 3000 else texto

    tematicas_str = ", ".join(TEMATICAS_DISPONIBLES)
    grupos_str = ", ".join(GRUPOS)

    prompt = f"""Analiza esta iniciativa parlamentaria del Parlamento de Andalucía y devuelve ÚNICAMENTE un objeto JSON con esta estructura exacta:

{{
  "resumen": "Resumen en 3-4 líneas en lenguaje claro para cualquier ciudadano. Sin tecnicismos.",
  "tematicas": ["Tema1", "Tema2"],
  "posicion_grupos": {{
    "PP-A": "A favor",
    "PSOE-A": "En contra",
    "Vox": "A favor",
    "Por Andalucía": "En contra",
    "Adelante Andalucía": "En contra"
  }}
}}

Reglas:
- "tematicas": elige entre estas opciones: {tematicas_str}. Máximo 3.
- "posicion_grupos": para cada grupo usa "A favor", "En contra", "Abstención" o "Desconocido".
  Infiere la posición según la ideología del grupo y el contenido de la iniciativa.
  PP-A y Vox suelen ser afines. PSOE-A, Por Andalucía y Adelante Andalucía suelen ser afines.

INICIATIVA:
Tipo: {tipo}
Título: {titulo}
Texto: {texto_recortado}

JSON:"""

    resultado_raw = _llamar_ia(prompt, max_tokens=600)
    resultado = _extraer_json(resultado_raw)

    # Valores por defecto si la IA falla o devuelve estructura incorrecta
    resumen = resultado.get("resumen", "")
    if not resumen or len(resumen) < 20:
        resumen = f"Iniciativa de tipo '{tipo}': {titulo[:200]}"

    tematicas = resultado.get("tematicas", [])
    if not isinstance(tematicas, list):
        tematicas = []
    tematicas = [t for t in tematicas if t in TEMATICAS_DISPONIBLES][:3]
    if not tematicas:
        tematicas = ["Administración pública"]

    posicion_grupos = resultado.get("posicion_grupos", {})
    posiciones_validas = {"A favor", "En contra", "Abstención", "Desconocido"}
    posicion_limpia = {}
    for grupo in GRUPOS:
        pos = posicion_grupos.get(grupo, "Desconocido")
        posicion_limpia[grupo] = pos if pos in posiciones_validas else "Desconocido"

    return {
        "resumen": resumen,
        "tematicas": tematicas,
        "posicion_grupos": posicion_limpia,
    }
