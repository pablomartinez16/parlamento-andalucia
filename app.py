#!/usr/bin/env python3
"""
Flask app — sirve la web y la API JSON del seguimiento legislativo.
"""

import json
from pathlib import Path
from flask import Flask, jsonify, render_template, request, abort

app = Flask(__name__)

DATA_DIR   = Path(__file__).parent / "data"
INIC_FILE  = DATA_DIR / "iniciativas.json"
STATS_FILE = DATA_DIR / "stats.json"


def _leer(path: Path, defecto):
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return defecto


# ── Web ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── API ───────────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats():
    return jsonify(_leer(STATS_FILE, {}))


@app.route("/api/iniciativas")
def api_iniciativas():
    iniciativas = _leer(INIC_FILE, [])

    # Filtros opcionales por query param
    tipo    = request.args.get("tipo")
    grupo   = request.args.get("grupo")
    estado  = request.args.get("estado")
    tematica = request.args.get("tematica")
    q       = request.args.get("q", "").lower()

    if tipo:
        iniciativas = [i for i in iniciativas if i.get("tipo") == tipo]
    if grupo:
        iniciativas = [i for i in iniciativas if i.get("grupo") == grupo]
    if estado:
        iniciativas = [i for i in iniciativas if i.get("estado") == estado]
    if tematica:
        iniciativas = [i for i in iniciativas if tematica in i.get("tematicas", [])]
    if q:
        iniciativas = [
            i for i in iniciativas
            if q in i.get("titulo", "").lower()
            or q in i.get("resumen", "").lower()
        ]

    # Paginación
    try:
        pagina  = max(1, int(request.args.get("pagina", 1)))
        por_pag = max(1, min(100, int(request.args.get("por_pagina", 20))))
    except ValueError:
        pagina, por_pag = 1, 20

    total     = len(iniciativas)
    inicio    = (pagina - 1) * por_pag
    resultado = iniciativas[inicio : inicio + por_pag]

    return jsonify({
        "total":      total,
        "pagina":     pagina,
        "por_pagina": por_pag,
        "paginas":    (total + por_pag - 1) // por_pag,
        "datos":      resultado,
    })


@app.route("/api/iniciativas/<int:id>")
def api_iniciativa(id: int):
    iniciativas = _leer(INIC_FILE, [])
    for ini in iniciativas:
        if ini.get("id") == id:
            return jsonify(ini)
    abort(404)


@app.route("/api/tematicas")
def api_tematicas():
    stats = _leer(STATS_FILE, {})
    return jsonify(stats.get("tematicas", {}))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
