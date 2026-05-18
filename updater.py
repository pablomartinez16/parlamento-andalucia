#!/usr/bin/env python3
"""
Sistema de actualización automática via webhook GitHub.
Realiza git pull, pip install y reinicio de servicios de forma segura.
"""

import hashlib
import hmac
import json
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime

import config
from db import registrar_update_log

log = logging.getLogger(__name__)


class Updater:
    """Gestor de actualizaciones automáticas."""

    def __init__(self):
        self.repo_dir = Path(__file__).parent
        self.secret = config.WEBHOOK_SECRET
        self.updating = False

    def validar_webhook(self, payload: str, signature: str) -> bool:
        """Valida la firma HMAC del webhook de GitHub."""
        expected = "sha256=" + hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _ejecutar(self, cmd: str, cwd=None) -> tuple[bool, str, str]:
        """Ejecuta comando shell. Retorna (éxito, stdout, stderr)."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd or self.repo_dir,
                capture_output=True,
                text=True,
                timeout=config.WEBHOOK_TIMEOUT,
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Timeout ejecutando comando"
        except Exception as e:
            return False, "", str(e)

    def git_pull(self) -> tuple[bool, str]:
        """Realiza git pull. Retorna (éxito, mensaje)."""
        log.info("Iniciando git pull...")
        ok, stdout, stderr = self._ejecutar(
            f"git pull origin {config.WEBHOOK_BRANCH}"
        )
        mensaje = stdout or stderr
        if ok:
            log.info(f"Git pull exitoso: {stdout[:100]}")
        else:
            log.error(f"Error en git pull: {stderr}")
        return ok, mensaje

    def pip_install(self) -> tuple[bool, str]:
        """Instala dependencias si requirements.txt cambió."""
        log.info("Verificando cambios en requirements.txt...")
        
        ok, stdout, stderr = self._ejecutar(
            "git diff HEAD~1 HEAD -- requirements.txt"
        )
        
        if not stdout:
            log.info("requirements.txt no cambió, omitiendo pip install")
            return True, "Sin cambios"
        
        log.info("Instalando nuevas dependencias...")
        ok, stdout, stderr = self._ejecutar(
            "pip install -r requirements.txt"
        )
        
        if ok:
            log.info(f"Pip install exitoso")
        else:
            log.error(f"Error en pip install: {stderr}")
        
        return ok, stdout or stderr

    def reiniciar_servicio(self, servicio: str = "parlamento") -> tuple[bool, str]:
        """Reinicia servicio systemd."""
        log.info(f"Reiniciando servicio {servicio}...")
        ok, stdout, stderr = self._ejecutar(
            f"sudo systemctl restart {servicio}"
        )
        
        if ok:
            log.info(f"Servicio {servicio} reiniciado")
        else:
            log.error(f"Error al reiniciar servicio: {stderr}")
        
        return ok, stdout or stderr

    def verificar_sintaxis(self) -> bool:
        """Verifica sintaxis Python de archivos modificados."""
        log.info("Verificando sintaxis Python...")
        ok, stdout, stderr = self._ejecutar(
            "python3 -m py_compile app.py ia.py db.py config.py scrapers/*.py"
        )
        return ok

    def actualizar(self) -> dict:
        """Ejecuta el flujo completo de actualización."""
        if self.updating:
            return {
                "status": "en_progreso",
                "mensaje": "Ya hay una actualización en progreso"
            }

        self.updating = True
        resultado = {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "pasos": {}
        }

        try:
            # Paso 1: Git pull
            ok, msg = self.git_pull()
            resultado["pasos"]["git_pull"] = {"ok": ok, "mensaje": msg}
            if not ok:
                registrar_update_log("git_pull", "error", error=msg)
                return resultado

            # Paso 2: Verificar sintaxis
            ok = self.verificar_sintaxis()
            resultado["pasos"]["sintaxis"] = {"ok": ok}
            if not ok:
                log.error("Error de sintaxis en código modificado")
                registrar_update_log("sintaxis", "error")
                return resultado

            # Paso 3: Pip install (solo si cambió requirements.txt)
            ok, msg = self.pip_install()
            resultado["pasos"]["pip_install"] = {"ok": ok, "mensaje": msg}
            if not ok:
                log.warning(f"Pip install falló (no crítico): {msg}")
                registrar_update_log("pip_install", "warning", error=msg)

            # Paso 4: Reiniciar servicio
            ok, msg = self.reiniciar_servicio()
            resultado["pasos"]["reinicio"] = {"ok": ok, "mensaje": msg}
            
            if ok:
                resultado["status"] = "exitoso"
                registrar_update_log(
                    "actualizar",
                    "exitoso",
                    mensaje="Actualización completada"
                )
                log.info("Actualización completada exitosamente")
            else:
                resultado["status"] = "error_reinicio"
                registrar_update_log("reinicio", "error", error=msg)

        except Exception as e:
            log.error(f"Error durante actualización: {e}")
            resultado["error"] = str(e)
            registrar_update_log("actualizar", "error", error=str(e))

        finally:
            self.updating = False

        return resultado

    def actualizar_async(self, callback=None):
        """Ejecuta actualización en thread separado."""
        def _actualizar():
            resultado = self.actualizar()
            if callback:
                callback(resultado)

        thread = threading.Thread(target=_actualizar, daemon=False)
        thread.start()
        return thread


# Instancia global
updater = Updater()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=config.LOG_FORMAT,
    )
    resultado = updater.actualizar()
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
