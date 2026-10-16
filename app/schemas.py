from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class TramiteSchema(BaseModel):
    id: Optional[int] = None
    fecha: Optional[date] = None
    numero_registro: Optional[str] = None
    descripcion: str
    organo_tramitador: Optional[str] = None
    sesion: Optional[str] = None
    url_bopa: Optional[str] = None
    url_diario: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentoSchema(BaseModel):
    id: Optional[int] = None
    tipo: str
    titulo: str
    url: str
    doc_id: Optional[str] = None
    fecha: Optional[date] = None

    class Config:
        from_attributes = True


class VotoGrupoSchema(BaseModel):
    grupo_nombre: str
    grupo_siglas: Optional[str] = None
    color_hex: Optional[str] = "#6c757d"
    sentido: str
    num_votos: int

    class Config:
        from_attributes = True


class VotacionSchema(BaseModel):
    id: int
    fecha: date
    sesion: Optional[str] = None
    organo: Optional[str] = None
    titulo: str
    votos_favor: int
    votos_contra: int
    abstenciones: int
    ausencias: int
    resultado: str
    url_fuente: Optional[str] = None
    desglose_grupos: List[VotoGrupoSchema] = []

    class Config:
        from_attributes = True


class IniciativaListSchema(BaseModel):
    id: int
    expediente: str
    titulo: str
    tipo: str
    proponente: Optional[str] = None
    estado: Optional[str] = None
    procedimiento: Optional[str] = None
    fecha_creacion: Optional[date] = None
    legislatura_romano: Optional[str] = None
    resumen_auto: Optional[str] = None

    class Config:
        from_attributes = True


class IniciativaDetailSchema(IniciativaListSchema):
    extracto: Optional[str] = None
    numero_registro: Optional[str] = None
    url_ficha: str
    created_at: datetime
    updated_at: datetime
    tramites: List[TramiteSchema] = []
    documentos: List[DocumentoSchema] = []
    votaciones: List[VotacionSchema] = []

    class Config:
        from_attributes = True


class StatsSchema(BaseModel):
    total_iniciativas: int
    por_tipo: dict
    por_estado: dict
    por_proponente: dict
    total_votaciones: int
