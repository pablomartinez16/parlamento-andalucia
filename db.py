#!/usr/bin/env python3
"""
Gestión de base de datos SQLite para seguimiento legislativo.
Unificado para Parlamento Andalucía y Congreso de Diputados.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "data" / "legislativo.db"
SCHEMA_VERSION = 1


def get_db_path() -> Path:
    """Retorna ruta de la base de datos."""
    DB_PATH.parent.mkdir(exist_ok=True)
    return DB_PATH


@contextmanager
def get_db():
    """Context manager para conexión a BD."""
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        log.error(f"Error BD: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """Crea esquema inicial si no existe."""
    with get_db() as conn:
        cur = conn.cursor()

        # Tabla de cámaras
        cur.execute("""
            CREATE TABLE IF NOT EXISTS camaras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                url_base TEXT NOT NULL,
                tipo_iniciativas TEXT NOT NULL,
                activo BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabla de iniciativas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS iniciativas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camara_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                numero TEXT UNIQUE,
                titulo TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                estado TEXT DEFAULT 'pendiente',
                fecha_presentacion TEXT,
                grupo_autor TEXT,
                texto_completo TEXT,
                resumen TEXT,
                fecha_scraping DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (camara_id) REFERENCES camaras(id)
            )
        """)

        # Tabla de temáticas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tematicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iniciativa_id INTEGER NOT NULL,
                tema TEXT NOT NULL,
                UNIQUE (iniciativa_id, tema),
                FOREIGN KEY (iniciativa_id) REFERENCES iniciativas(id) ON DELETE CASCADE
            )
        """)

        # Tabla de votaciones
        cur.execute("""
            CREATE TABLE IF NOT EXISTS votos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iniciativa_id INTEGER UNIQUE NOT NULL,
                favor INTEGER DEFAULT 0,
                contra INTEGER DEFAULT 0,
                abstencion INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (iniciativa_id) REFERENCES iniciativas(id) ON DELETE CASCADE
            )
        """)

        # Tabla de grupos parlamentarios
        cur.execute("""
            CREATE TABLE IF NOT EXISTS grupos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camara_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                ideologia TEXT,
                UNIQUE (camara_id, nombre),
                FOREIGN KEY (camara_id) REFERENCES camaras(id)
            )
        """)

        # Tabla de posiciones de grupos en iniciativas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS posiciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iniciativa_id INTEGER NOT NULL,
                grupo_id INTEGER NOT NULL,
                posicion TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (iniciativa_id, grupo_id),
                FOREIGN KEY (iniciativa_id) REFERENCES iniciativas(id) ON DELETE CASCADE,
                FOREIGN KEY (grupo_id) REFERENCES grupos(id) ON DELETE CASCADE
            )
        """)

        # Tabla de logs del scraper
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scraper_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camara_id INTEGER NOT NULL,
                fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
                fecha_fin DATETIME,
                estado TEXT,
                nuevas_iniciativas INTEGER DEFAULT 0,
                errores INTEGER DEFAULT 0,
                log_texto TEXT,
                FOREIGN KEY (camara_id) REFERENCES camaras(id)
            )
        """)

        # Tabla de logs de actualización
        cur.execute("""
            CREATE TABLE IF NOT EXISTS update_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                tipo TEXT,
                status TEXT,
                mensaje TEXT,
                error TEXT
            )
        """)

        # Tabla de versión de schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices para búsquedas frecuentes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iniciativas_camara ON iniciativas(camara_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iniciativas_estado ON iniciativas(estado)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iniciativas_tipo ON iniciativas(tipo)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_iniciativas_grupo ON iniciativas(grupo_autor)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tematicas_iniciativa ON tematicas(iniciativa_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_posiciones_iniciativa ON posiciones(iniciativa_id)")

        # Full-text search
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS iniciativas_fts 
            USING fts5(titulo, resumen, content=iniciativas, content_rowid=id)
        """)

        # Registrar versión si no existe
        cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        if cur.fetchone() is None:
            cur.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))

        conn.commit()
        log.info("Base de datos inicializada")


def cargar_camaras_defecto():
    """Carga cámaras por defecto si no existen."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM camaras")
        if cur.fetchone()[0] == 0:
            camaras = [
                ("Congreso de Diputados", "https://www.congreso.es", "PL,PPL,PNL,Mociones,Decretos"),
                ("Parlamento de Andalucía", "https://www.parlamentodeandalucia.es", "PL,PPL,PNL,Mociones,Decretos"),
            ]
            cur.executemany(
                "INSERT INTO camaras (nombre, url_base, tipo_iniciativas) VALUES (?, ?, ?)",
                camaras,
            )
            conn.commit()
            log.info("Cámaras por defecto cargadas")


def obtener_camara(nombre: str) -> dict:
    """Obtiene cámara por nombre."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM camaras WHERE nombre = ?", (nombre,))
        row = cur.fetchone()
        return dict(row) if row else None


def obtener_iniciativa(id_iniciativa: int) -> dict:
    """Obtiene iniciativa por ID."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT i.*, c.nombre as camara_nombre
            FROM iniciativas i
            JOIN camaras c ON i.camara_id = c.id
            WHERE i.id = ?
        """, (id_iniciativa,))
        return dict(cur.fetchone()) if cur.fetchone() else None


def insertar_iniciativa(camara_id: int, datos: dict) -> int:
    """Inserta nueva iniciativa. Retorna el ID."""
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO iniciativas (
                    camara_id, tipo, numero, titulo, url, estado,
                    fecha_presentacion, grupo_autor, texto_completo, resumen, fecha_scraping
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                camara_id,
                datos.get("tipo"),
                datos.get("numero"),
                datos.get("titulo"),
                datos.get("url"),
                datos.get("estado", "pendiente"),
                datos.get("fecha_presentacion"),
                datos.get("grupo_autor"),
                datos.get("texto_completo"),
                datos.get("resumen"),
                datetime.now().isoformat(),
            ))
            iniciativa_id = cur.lastrowid

            # Insertar temáticas
            for tema in datos.get("tematicas", []):
                cur.execute(
                    "INSERT OR IGNORE INTO tematicas (iniciativa_id, tema) VALUES (?, ?)",
                    (iniciativa_id, tema),
                )

            # Insertar votos
            votos = datos.get("votos", {})
            if votos:
                cur.execute("""
                    INSERT INTO votos (iniciativa_id, favor, contra, abstencion)
                    VALUES (?, ?, ?, ?)
                """, (
                    iniciativa_id,
                    votos.get("favor", 0),
                    votos.get("contra", 0),
                    votos.get("abstencion", 0),
                ))

            # Insertar posiciones de grupos
            for grupo_nombre, posicion in datos.get("posicion_grupos", {}).items():
                cur.execute("""
                    SELECT id FROM grupos WHERE camara_id = ? AND nombre = ?
                """, (camara_id, grupo_nombre))
                grupo = cur.fetchone()
                if grupo:
                    cur.execute("""
                        INSERT OR REPLACE INTO posiciones (iniciativa_id, grupo_id, posicion)
                        VALUES (?, ?, ?)
                    """, (iniciativa_id, grupo[0], posicion))

            conn.commit()
            return iniciativa_id
        except sqlite3.IntegrityError as e:
            log.warning(f"Iniciativa ya existe: {e}")
            return None


def obtener_iniciativas(camara_id: int = None, tipo: str = None, estado: str = None,
                       grupo: str = None, tema: str = None, q: str = None,
                       pagina: int = 1, por_pagina: int = 20) -> tuple:
    """
    Obtiene iniciativas con filtros. Retorna (total, datos).
    """
    with get_db() as conn:
        cur = conn.cursor()
        
        query = "SELECT DISTINCT i.* FROM iniciativas i"
        count_query = "SELECT COUNT(DISTINCT i.id) FROM iniciativas i"
        params = []
        
        if tema:
            query += " JOIN tematicas t ON i.id = t.iniciativa_id"
            count_query += " JOIN tematicas t ON i.id = t.iniciativa_id"
        
        query += " WHERE 1=1"
        count_query += " WHERE 1=1"
        
        if camara_id:
            query += " AND i.camara_id = ?"
            count_query += " AND i.camara_id = ?"
            params.append(camara_id)
        if tipo:
            query += " AND i.tipo = ?"
            count_query += " AND i.tipo = ?"
            params.append(tipo)
        if estado:
            query += " AND i.estado = ?"
            count_query += " AND i.estado = ?"
            params.append(estado)
        if grupo:
            query += " AND i.grupo_autor = ?"
            count_query += " AND i.grupo_autor = ?"
            params.append(grupo)
        if tema:
            query += " AND t.tema = ?"
            count_query += " AND t.tema = ?"
            params.append(tema)
        
        if q:
            # Búsqueda simple por título o resumen
            query += " AND (i.titulo LIKE ? OR i.resumen LIKE ?)"
            count_query += " AND (i.titulo LIKE ? OR i.resumen LIKE ?)"
            search_term = f"%{q}%"
            params.extend([search_term, search_term])
        
        # Contar total (ejecutar con copia de params)
        cur.execute(count_query, params[:len(params)])
        total = cur.fetchone()[0]
        
        # Paginar
        offset = (pagina - 1) * por_pagina
        query += f" ORDER BY i.created_at DESC LIMIT ? OFFSET ?"
        params.extend([por_pagina, offset])
        
        cur.execute(query, params)
        datos = [dict(row) for row in cur.fetchall()]
        
        return total, datos


def obtener_estadisticas(camara_id: int = None) -> dict:
    """Obtiene estadísticas de iniciativas por cámara."""
    with get_db() as conn:
        cur = conn.cursor()
        
        where = f"WHERE camara_id = {camara_id}" if camara_id else ""
        
        cur.execute(f"SELECT COUNT(*) FROM iniciativas {where}")
        total = cur.fetchone()[0]
        
        cur.execute(f"SELECT estado, COUNT(*) FROM iniciativas {where} GROUP BY estado")
        estados = dict(cur.fetchall())
        
        cur.execute(f"""
            SELECT t.tema, COUNT(*) as count 
            FROM tematicas t
            JOIN iniciativas i ON t.iniciativa_id = i.id
            {where}
            GROUP BY t.tema
            ORDER BY count DESC
            LIMIT 10
        """)
        tematicas = dict(cur.fetchall())
        
        return {
            "total": total,
            "estados": estados,
            "tematicas": tematicas,
        }


def registrar_scraper_log(camara_id: int, estado: str, nuevas: int = 0, 
                         errores: int = 0, log_texto: str = ""):
    """Registra log de ejecución del scraper."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO scraper_log 
            (camara_id, fecha_fin, estado, nuevas_iniciativas, errores, log_texto)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
        """, (camara_id, estado, nuevas, errores, log_texto))
        conn.commit()


def registrar_update_log(tipo: str, status: str, mensaje: str = "", error: str = ""):
    """Registra log de actualización automática."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO update_log (tipo, status, mensaje, error)
            VALUES (?, ?, ?, ?)
        """, (tipo, status, mensaje, error))
        conn.commit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    cargar_camaras_defecto()
    print("✓ Base de datos inicializada")
