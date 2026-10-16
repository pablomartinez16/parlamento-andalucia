import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Legislatura, Iniciativa, Tramite, Documento
from app.scrapers.iniciativas import IniciativaScraper
from app.scrapers.rss import RSSScraper
from app.services.resumen import ResumenService

logger = logging.getLogger(__name__)


class IngestaService:
    """
    Orchestrates idempotent and incremental ingestion of parliamentary initiatives.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.iniciativa_scraper = IniciativaScraper()
        self.rss_scraper = RSSScraper()

    async def ensure_legislatura(self, numero: int) -> Legislatura:
        stmt = select(Legislatura).where(Legislatura.numero == numero)
        result = await self.db.execute(stmt)
        leg = result.scalar_one_or_none()
        if not leg:
            romanos = {11: "XI", 12: "XII", 13: "XIII", 14: "XIV"}
            romano = romanos.get(numero, f"{numero}ª")
            leg = Legislatura(
                numero=numero,
                romano=romano,
                nombre=f"{romano} Legislatura"
            )
            self.db.add(leg)
            await self.db.flush()
        return leg

    async def ingest_iniciativa_by_expediente(self, expediente: str) -> Optional[Iniciativa]:
        """
        Fetches official details and upserts the initiative idempotently.
        """
        logger.info(f"Ingesting initiative {expediente}...")
        data = await self.iniciativa_scraper.get_iniciativa(expediente)
        if not data:
            logger.warning(f"No data returned for expediente {expediente}")
            return None

        leg = await self.ensure_legislatura(data["legislatura_numero"])

        stmt = select(Iniciativa).where(Iniciativa.expediente == expediente)
        res = await self.db.execute(stmt)
        iniciativa = res.scalar_one_or_none()

        if not iniciativa:
            iniciativa = Iniciativa(
                expediente=expediente,
                legislatura_id=leg.id,
                titulo=data["titulo"],
                extracto=data["extracto"],
                tipo=data["tipo"],
                proponente=data["proponente"],
                estado=data["estado"],
                procedimiento=data["procedimiento"],
                numero_registro=data["numero_registro"],
                fecha_creacion=data["fecha_creacion"],
                url_ficha=data["url_ficha"],
            )
            self.db.add(iniciativa)
            await self.db.flush()
        else:
            # Update mutable fields
            iniciativa.titulo = data["titulo"]
            iniciativa.extracto = data["extracto"]
            iniciativa.tipo = data["tipo"]
            iniciativa.proponente = data["proponente"]
            iniciativa.estado = data["estado"]
            iniciativa.procedimiento = data["procedimiento"]
            iniciativa.numero_registro = data["numero_registro"]
            iniciativa.fecha_creacion = data["fecha_creacion"]
            iniciativa.url_ficha = data["url_ficha"]

        # Generate summary if requested and not present
        if not iniciativa.resumen_auto:
            iniciativa.resumen_auto = await ResumenService.generar_resumen(
                iniciativa.titulo, iniciativa.extracto, iniciativa.tipo
            )

        # Clear and re-populate tramites to guarantee latest timeline idempotently
        # Or alternatively update/insert
        for t_data in data.get("tramites", []):
            tramite = Tramite(
                iniciativa_id=iniciativa.id,
                fecha=t_data["fecha"],
                numero_registro=t_data.get("numero_registro"),
                descripcion=t_data["descripcion"],
                organo_tramitador=t_data.get("organo_tramitador"),
                sesion=t_data.get("sesion"),
            )
            self.db.add(tramite)

        # Add documents
        for d_data in data.get("documentos", []):
            doc_stmt = select(Documento).where(
                Documento.iniciativa_id == iniciativa.id,
                Documento.url == d_data["url"]
            )
            doc_res = await self.db.execute(doc_stmt)
            if not doc_res.scalar_one_or_none():
                doc = Documento(
                    iniciativa_id=iniciativa.id,
                    tipo=d_data["tipo"],
                    titulo=d_data["titulo"],
                    url=d_data["url"],
                    doc_id=d_data.get("doc_id")
                )
                self.db.add(doc)

        await self.db.commit()
        await self.db.refresh(iniciativa)
        return iniciativa

    async def sync_from_rss(self) -> int:
        """
        Polls the RSS feeds (Iniciativas + Leyes) and updates or inserts new initiatives.
        Returns the number of ingested/refreshed initiatives.
        """
        count = 0
        try:
            iniciativas_items = await self.rss_scraper.get_iniciativas_feed()
            leyes_items = await self.rss_scraper.get_leyes_feed()
            all_items = iniciativas_items + leyes_items
            
            seen_exps = set()
            for item in all_items:
                exp = item.get("expediente")
                if exp and exp not in seen_exps:
                    seen_exps.add(exp)
                    try:
                        res = await self.ingest_iniciativa_by_expediente(exp)
                        if res:
                            count += 1
                    except Exception as e:
                        logger.error(f"Error ingesting RSS item {exp}: {e}")

        except Exception as e:
            logger.error(f"Error reading RSS feeds: {e}")

        return count
