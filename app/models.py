from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey, 
    Index, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class Legislatura(Base):
    __tablename__ = "legislaturas"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(Integer, unique=True, nullable=False, index=True) # e.g. 12, 13
    romano = Column(String(10), nullable=False) # e.g. "XII", "XIII"
    nombre = Column(String(100), nullable=False) # e.g. "XIII Legislatura"
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)

    iniciativas = relationship("Iniciativa", back_populates="legislatura", cascade="all, delete-orphan")
    grupos = relationship("GrupoParlamentario", back_populates="legislatura")
    diputados = relationship("Diputado", back_populates="legislatura")

    def __repr__(self) -> str:
        return f"<Legislatura {self.romano}>"


class GrupoParlamentario(Base):
    __tablename__ = "grupos_parlamentarios"

    id = Column(Integer, primary_key=True, index=True)
    legislatura_id = Column(Integer, ForeignKey("legislaturas.id", ondelete="CASCADE"), nullable=False)
    nombre = Column(String(200), nullable=False)
    siglas = Column(String(50), nullable=True)
    color_hex = Column(String(7), nullable=True, default="#6c757d") # CSS color for charts

    legislatura = relationship("Legislatura", back_populates="grupos")
    diputados = relationship("Diputado", back_populates="grupo")
    votos_grupo = relationship("VotoGrupo", back_populates="grupo")

    __table_args__ = (
        UniqueConstraint("legislatura_id", "nombre", name="uq_grupo_legislatura_nombre"),
    )

    def __repr__(self) -> str:
        return f"<GrupoParlamentario {self.siglas or self.nombre}>"


class Diputado(Base):
    __tablename__ = "diputados"

    id = Column(Integer, primary_key=True, index=True)
    legislatura_id = Column(Integer, ForeignKey("legislaturas.id", ondelete="CASCADE"), nullable=False)
    grupo_id = Column(Integer, ForeignKey("grupos_parlamentarios.id", ondelete="SET NULL"), nullable=True)
    nombre_completo = Column(String(250), nullable=False, index=True)
    circunscripcion = Column(String(100), nullable=True) # Almería, Cádiz, Córdoba, Granada, Huelva, Jaén, Málaga, Sevilla

    legislatura = relationship("Legislatura", back_populates="diputados")
    grupo = relationship("GrupoParlamentario", back_populates="diputados")
    votos = relationship("VotoDiputado", back_populates="diputado")

    __table_args__ = (
        UniqueConstraint("legislatura_id", "nombre_completo", name="uq_diputado_leg_nombre"),
    )

    def __repr__(self) -> str:
        return f"<Diputado {self.nombre_completo}>"


class Iniciativa(Base):
    __tablename__ = "iniciativas"

    id = Column(Integer, primary_key=True, index=True)
    expediente = Column(String(50), unique=True, nullable=False, index=True) # e.g. 13-26/PPL-000002
    legislatura_id = Column(Integer, ForeignKey("legislaturas.id", ondelete="CASCADE"), nullable=False)
    
    titulo = Column(Text, nullable=False)
    tipo = Column(String(100), nullable=False, index=True) # Proposiciones de Ley, Proyectos de Ley, etc.
    subtipo = Column(String(100), nullable=True)
    proponente = Column(String(255), nullable=True, index=True)
    estado = Column(String(100), nullable=True, index=True) # En tramitación, Aprobada, Rechazada, Decaída
    procedimiento = Column(String(100), nullable=True) # Ordinario, Lectura única, etc.
    numero_registro = Column(String(50), nullable=True)
    
    fecha_creacion = Column(Date, nullable=True, index=True)
    extracto = Column(Text, nullable=True)
    resumen_auto = Column(Text, nullable=True) # Resumen generado por LLM (objetivo, en lenguaje llano)
    
    url_ficha = Column(String(500), nullable=False)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    legislatura = relationship("Legislatura", back_populates="iniciativas")
    tramites = relationship("Tramite", back_populates="iniciativa", cascade="all, delete-orphan", order_by="Tramite.fecha.desc()")
    documentos = relationship("Documento", back_populates="iniciativa", cascade="all, delete-orphan")
    votaciones = relationship("Votacion", back_populates="iniciativa", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_iniciativas_tipo_estado", "tipo", "estado"),
        Index("idx_iniciativas_fecha_creacion", "fecha_creacion"),
    )

    def __repr__(self) -> str:
        return f"<Iniciativa {self.expediente}>"


class Tramite(Base):
    __tablename__ = "tramites"

    id = Column(Integer, primary_key=True, index=True)
    iniciativa_id = Column(Integer, ForeignKey("iniciativas.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha = Column(Date, nullable=True, index=True)
    numero_registro = Column(String(50), nullable=True)
    descripcion = Column(Text, nullable=False)
    organo_tramitador = Column(String(200), nullable=True)
    sesion = Column(String(50), nullable=True)
    url_bopa = Column(String(500), nullable=True)
    url_diario = Column(String(500), nullable=True)

    iniciativa = relationship("Iniciativa", back_populates="tramites")

    def __repr__(self) -> str:
        return f"<Tramite {self.fecha} - {self.descripcion[:30]}>"


class Documento(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, index=True)
    iniciativa_id = Column(Integer, ForeignKey("iniciativas.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False) # BOPA, DIARIO, OTRO
    titulo = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    doc_id = Column(String(50), nullable=True) # id numérico del documento en webdinamica
    fecha = Column(Date, nullable=True)

    iniciativa = relationship("Iniciativa", back_populates="documentos")

    def __repr__(self) -> str:
        return f"<Documento {self.tipo} - {self.titulo}>"


class Votacion(Base):
    __tablename__ = "votaciones"

    id = Column(Integer, primary_key=True, index=True)
    iniciativa_id = Column(Integer, ForeignKey("iniciativas.id", ondelete="CASCADE"), nullable=True, index=True)
    fecha = Column(Date, nullable=False, index=True)
    sesion = Column(String(50), nullable=True)
    organo = Column(String(150), nullable=True) # Pleno, Comisión de Salud, etc.
    titulo = Column(Text, nullable=False) # Asunto votado
    
    votos_favor = Column(Integer, default=0, nullable=False)
    votos_contra = Column(Integer, default=0, nullable=False)
    abstenciones = Column(Integer, default=0, nullable=False)
    ausencias = Column(Integer, default=0, nullable=False)
    resultado = Column(String(50), nullable=False, index=True) # Aprobada, Rechazada, Empate
    
    url_fuente = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    iniciativa = relationship("Iniciativa", back_populates="votaciones")
    desglose_grupos = relationship("VotoGrupo", back_populates="votacion", cascade="all, delete-orphan")
    desglose_diputados = relationship("VotoDiputado", back_populates="votacion", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Votacion {self.fecha} - {self.resultado}>"


class VotoGrupo(Base):
    __tablename__ = "votos_grupo"

    id = Column(Integer, primary_key=True, index=True)
    votacion_id = Column(Integer, ForeignKey("votaciones.id", ondelete="CASCADE"), nullable=False, index=True)
    grupo_id = Column(Integer, ForeignKey("grupos_parlamentarios.id", ondelete="CASCADE"), nullable=False)
    
    sentido = Column(String(20), nullable=False) # FAVOR, CONTRA, ABSTENCION, LIBRE
    num_votos = Column(Integer, nullable=False, default=0)

    votacion = relationship("Votacion", back_populates="desglose_grupos")
    grupo = relationship("GrupoParlamentario", back_populates="votos_grupo")

    def __repr__(self) -> str:
        return f"<VotoGrupo {self.sentido} ({self.num_votos})>"


class VotoDiputado(Base):
    __tablename__ = "votos_diputado"

    id = Column(Integer, primary_key=True, index=True)
    votacion_id = Column(Integer, ForeignKey("votaciones.id", ondelete="CASCADE"), nullable=False, index=True)
    diputado_id = Column(Integer, ForeignKey("diputados.id", ondelete="CASCADE"), nullable=False, index=True)
    
    sentido = Column(String(20), nullable=False) # FAVOR, CONTRA, ABSTENCION, AUSENTE, DELEGADO

    votacion = relationship("Votacion", back_populates="desglose_diputados")
    diputado = relationship("Diputado", back_populates="votos")

    __table_args__ = (
        UniqueConstraint("votacion_id", "diputado_id", name="uq_voto_votacion_diputado"),
    )

    def __repr__(self) -> str:
        return f"<VotoDiputado {self.sentido}>"
