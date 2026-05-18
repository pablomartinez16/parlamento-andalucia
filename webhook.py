#!/usr/bin/env python3
"""
webhook.py — Escucha push de GitHub y despliega automáticamente.
Corre en :9000, detrás de tu Nginx reverse proxy.

Flujo:
  GitHub push → Nginx → :9000/webhook → git pull → pip install → restart gunicorn
"""

import hashlib
import hmac
import json
import logging
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Config ────────────────────────────────────────────────────────
PORT         = 9000
SECRET       = os.environ.get("WEBHOOK_SECRET", "")   # se lee de /etc/parlamento.env
INSTALL_DIR  = "/opt/parlamento"
APP_USER     = "parlamento"
BRANCH       = "main"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{INSTALL_DIR}/webhook.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ── Verificación de firma HMAC (seguridad) ────────────────────────
def verificar_firma(payload: bytes, header_sig: str) -> bool:
    if not SECRET:
        log.warning("WEBHOOK_SECRET no configurado — aceptando sin verificar firma.")
        return True
    if not header_sig or not header_sig.startswith("sha256="):
        return False
    esperada = "sha256=" + hmac.new(
        SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperada, header_sig)


# ── Deploy ────────────────────────────────────────────────────────
def ejecutar(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    log.info("$ %s", " ".join(cmd))
    return subprocess.run(
        cmd, capture_output=True, text=True,
        cwd=INSTALL_DIR, **kwargs
    )

def desplegar() -> tuple[bool, str]:
    pasos = []

    # 1. git pull
    r = ejecutar(["sudo", "-u", APP_USER, "git", "pull", "origin", BRANCH])
    pasos.append(("git pull", r))
    if r.returncode != 0:
        return False, f"git pull falló:\n{r.stderr}"

    salida_pull = r.stdout.strip()
    if salida_pull == "Already up to date.":
        return True, "Sin cambios en el repo."

    # 2. pip install (por si cambiaron requirements.txt)
    r = ejecutar([
        "sudo", "-u", APP_USER,
        f"{INSTALL_DIR}/venv/bin/pip", "install",
        "-r", f"{INSTALL_DIR}/requirements.txt", "-q"
    ])
    pasos.append(("pip install", r))
    if r.returncode != 0:
        return False, f"pip install falló:\n{r.stderr}"

    # 3. reiniciar gunicorn
    r = ejecutar(["systemctl", "restart", "parlamento"])
    pasos.append(("systemctl restart", r))
    if r.returncode != 0:
        return False, f"restart falló:\n{r.stderr}"

    log.info("Deploy completado. Pull: %s", salida_pull)
    return True, salida_pull


# ── HTTP handler ──────────────────────────────────────────────────
class WebhookHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        log.info(fmt % args)

    def _responder(self, code: int, msg: str):
        body = json.dumps({"mensaje": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._responder(200, "ok")
        else:
            self._responder(404, "no encontrado")

    def do_POST(self):
        if self.path != "/webhook":
            self._responder(404, "no encontrado")
            return

        longitud = int(self.headers.get("Content-Length", 0))
        payload  = self.rfile.read(longitud)
        firma    = self.headers.get("X-Hub-Signature-256", "")

        if not verificar_firma(payload, firma):
            log.warning("Firma inválida — petición rechazada.")
            self._responder(403, "firma inválida")
            return

        try:
            datos = json.loads(payload)
        except json.JSONDecodeError:
            self._responder(400, "JSON inválido")
            return

        # Solo actuamos en push a la rama configurada
        ref = datos.get("ref", "")
        if ref != f"refs/heads/{BRANCH}":
            self._responder(200, f"rama ignorada: {ref}")
            return

        pusher  = datos.get("pusher", {}).get("name", "desconocido")
        commits = len(datos.get("commits", []))
        log.info("Push de %s (%d commit/s) — iniciando deploy…", pusher, commits)

        ok, msg = desplegar()
        if ok:
            log.info("Deploy OK: %s", msg)
            self._responder(200, msg)
        else:
            log.error("Deploy FALLÓ: %s", msg)
            self._responder(500, msg)


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not SECRET:
        log.warning("=" * 60)
        log.warning("WEBHOOK_SECRET vacío. Configúralo en /etc/parlamento.env")
        log.warning("=" * 60)

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    log.info("Webhook escuchando en :%d /webhook", PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Webhook detenido.")
