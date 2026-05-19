#!/usr/bin/env python3
"""Script para inspeccionar la estructura del JSON del Congreso."""

import json
import requests

OPENDATA_URL = "https://www.congreso.es/es/opendata/iniciativas"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def get_json_urls():
    """Obtiene URLs de los JSONs."""
    try:
        resp = requests.get(OPENDATA_URL, headers=HEADERS, timeout=30)
        import re
        urls_json = re.findall(
            r'(?:https://www\.congreso\.es)?(/webpublica/opendata/iniciativas/[^"]+\.json)',
            resp.text
        )
        
        for url in urls_json:
            if url.startswith('/'):
                url = f"https://www.congreso.es{url}"
            return url  # Retorna la primera
    except Exception as e:
        print(f"Error: {e}")
    return None

def main():
    url = get_json_urls()
    if not url:
        print("No se encontró URL JSON")
        return
    
    print(f"Descargando: {url}\n")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        datos = json.loads(resp.text)
        
        if datos and len(datos) > 0:
            print("=== PRIMER REGISTRO ===\n")
            print(json.dumps(datos[0], indent=2, ensure_ascii=False))
            
            print("\n\n=== CAMPOS DISPONIBLES ===")
            print("Campos:", list(datos[0].keys()))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
