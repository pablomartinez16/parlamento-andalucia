#!/usr/bin/env python3
"""
Flask app — sirve la web y la API JSON de seguimiento legislativo.
Soporta múltiples cámaras legislativas (Congreso + Parlamento Andalucía).
"""

import json
import logging
from datetime import datetime
from functools import wraps

import config
import db
from flask import Flask, jsonify, render_template, request, abort
from updater import updater

app = Flask(__name__)
app.secret_key = config.WEBHOOK_SECRET

logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
)
log = logging.getLogger(__name__)

# ── Inicialización ─────────────────────────────────────────
db.init_db()
db.cargar_camaras_defecto()


# ── Middleware ─────────────────────────────────────────────
def require_camara(f):
    """Decorator para validar que se proporciona una cámara válida."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        camara_nombre = request.args.get("camara", "Congreso de Diputados")
        camara = db.obtener_camara(camara_nombre)
        if not camara:
            return jsonify({"error": f"Cámara '{camara_nombre}' no encontrada"}), 400
        kwargs["camara_id"] = camara["id"]
        return f(*args, **kwargs)
    return decorated_function


# ── Web ────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/congreso")
def congreso():
    return render_template("congreso.html")


@app.route("/parlamento")
def parlamento_new():
    return render_template("andalucia.html")


@app.route("/andalucia")
def parlamento():
    return render_template("andalucia.html")


# ── API: Estadísticas ──────────────────────────────────────
@app.route("/api/stats")
@require_camara
def api_stats(camara_id):
    stats = db.obtener_estadisticas(camara_id)
    camara = db.obtener_camara(request.args.get("camara", "Congreso de Diputados"))
    
    return jsonify({
        "camara": camara["nombre"] if camara else "Desconocida",
        **stats,
        "ultima_actualizacion": datetime.now().isoformat(),
    })


# ── API: Iniciativas ───────────────────────────────────────
@app.route("/api/iniciativas")
@require_camara
def api_iniciativas(camara_id):
    # Parámetros de filtro
    tipo = request.args.get("tipo")
    grupo = request.args.get("grupo")
    estado = request.args.get("estado")
    tema = request.args.get("tema")
    q = request.args.get("q", "").strip()
    
    # Paginación
    try:
        pagina = max(1, int(request.args.get("pagina", 1)))
        por_pagina = max(1, min(
            config.API_MAX_ITEMS_PER_PAGE,
            int(request.args.get("por_pagina", config.API_ITEMS_PER_PAGE))
        ))
    except ValueError:
        pagina, por_pagina = 1, config.API_ITEMS_PER_PAGE
    
    total, datos = db.obtener_iniciativas(
        camara_id=camara_id,
        tipo=tipo,
        estado=estado,
        grupo=grupo,
        tema=tema,
        q=q,
        pagina=pagina,
        por_pagina=por_pagina,
    )
    
    return jsonify({
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "paginas": (total + por_pagina - 1) // por_pagina,
        "datos": datos,
    })


@app.route("/api/iniciativas/<int:id>")
def api_iniciativa(id):
    ini = db.obtener_iniciativa(id)
    if not ini:
        abort(404)
    return jsonify(ini)


# ── API: Temáticas ────────────────────────────────────────
@app.route("/api/tematicas")
@require_camara
def api_tematicas(camara_id):
    stats = db.obtener_estadisticas(camara_id)
    return jsonify(stats.get("tematicas", {}))


# ── API: Sistema ───────────────────────────────────────────
@app.route("/api/system/status")
def api_system_status():
    """Estado del sistema (versión, última actualización, etc.)."""
    with db.get_db() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM update_log 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        updates = [dict(row) for row in cur.fetchall()]
        
        cur.execute("""
            SELECT c.nombre, sl.* FROM scraper_log sl
            JOIN camaras c ON sl.camara_id = c.id
            ORDER BY sl.fecha_inicio DESC
            LIMIT 5
        """)
        scraper_logs = [dict(row) for row in cur.fetchall()]
    
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "ultimas_actualizaciones": updates,
        "ultimos_scrapers": scraper_logs,
    })


# ── Webhook de Actualización ───────────────────────────────
@app.route("/webhook/update", methods=["POST"])
def webhook_update():
    """
    Endpoint para webhook de GitHub.
    Requiere header: X-Hub-Signature-256
    """
    signature = request.headers.get("X-Hub-Signature-256", "")
    payload = request.get_data()
    
    if not updater.validar_webhook(payload.decode(), signature):
        log.warning("Webhook con firma inválida rechazado")
        return jsonify({"error": "Firma inválida"}), 401
    
    log.info("Webhook recibido, iniciando actualización...")
    resultado = updater.actualizar()
    
    return jsonify(resultado), 200 if resultado["status"] == "exitoso" else 500


@app.route("/api/update/check", methods=["GET"])
def api_update_check():
    """Endpoint para chequear manualmente el estado de actualización."""
    return jsonify({
        "updating": updater.updating,
        "timestamp": datetime.now().isoformat(),
    })


# ── Manejadores de errores ─────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "No encontrado"}), 404


@app.errorhandler(500)
def server_error(error):
    log.error(f"Error interno: {error}")
    return jsonify({"error": "Error interno del servidor"}), 500


if __name__ == "__main__":
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
