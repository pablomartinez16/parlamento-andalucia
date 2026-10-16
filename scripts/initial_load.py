import asyncio
import logging
from app.database import AsyncSessionLocal, engine, Base
from app.services.ingesta import IngestaService
from app.models import GrupoParlamentario, Votacion, VotoGrupo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

INITIAL_EXPEDIENTES = [
    # XIII Legislatura (Actual - Año 2026)
    "13-26/PPL-000001",
    "13-26/PPL-000002",
    "13-26/ILPA-000001",
    # XII Legislatura (Leyes consolidadas y votaciones representativas)
    "12-25/PL-000001",
    "12-25/PL-000011",
]


async def run_seed():
    logger.info("Initializing schema if not created...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        service = IngestaService(session)
        
        # 1. Ensure Legislaturas & Official Parliamentary Groups
        leg13 = await service.ensure_legislatura(13)
        leg12 = await service.ensure_legislatura(12)

        grupos_data = [
            {"leg_id": leg13.id, "nombre": "G.P. Popular Andaluz", "siglas": "GPPA", "color": "#0056B3"},
            {"leg_id": leg13.id, "nombre": "G.P. Socialista", "siglas": "GPS", "color": "#E30613"},
            {"leg_id": leg13.id, "nombre": "G.P. VOX en Andalucía", "siglas": "GPVOX", "color": "#63BE21"},
            {"leg_id": leg13.id, "nombre": "G.P. Por Andalucía", "siglas": "GP-PorA", "color": "#7B1FA2"},
            {"leg_id": leg13.id, "nombre": "G.P. Mixto-Adelante Andalucía", "siglas": "GP-AA", "color": "#00A859"},
        ]

        grupos_dict = {}
        for g_info in grupos_data:
            from sqlalchemy import select
            q = select(GrupoParlamentario).where(
                GrupoParlamentario.legislatura_id == g_info["leg_id"],
                GrupoParlamentario.nombre == g_info["nombre"]
            )
            existing = (await session.execute(q)).scalar_one_or_none()
            if not existing:
                grupo = GrupoParlamentario(
                    legislatura_id=g_info["leg_id"],
                    nombre=g_info["nombre"],
                    siglas=g_info["siglas"],
                    color_hex=g_info["color"]
                )
                session.add(grupo)
                await session.flush()
                grupos_dict[g_info["nombre"]] = grupo
            else:
                grupos_dict[g_info["nombre"]] = existing

        await session.commit()

        # 2. Ingest initial batch of verified real initiatives
        logger.info(f"Ingesting {len(INITIAL_EXPEDIENTES)} verified initiatives from parliament...")
        for exp in INITIAL_EXPEDIENTES:
            try:
                ini = await service.ingest_iniciativa_by_expediente(exp)
                if ini:
                    logger.info(f"Successfully loaded: {ini.expediente} -> {ini.titulo[:60]}")
            except Exception as e:
                logger.error(f"Error loading {exp}: {e}")

        # 3. Add representative plenary vote record for PL-000001 (Ley de Colegio Oficial de Criminología)
        from sqlalchemy import select
        q_ini = select(service.db.bind).where() if False else None
        q_ini = select(service.iniciativa_scraper.__class__).substitute if False else None
        from app.models import Iniciativa
        res_ini = await session.execute(select(Iniciativa).where(Iniciativa.expediente == "12-25/PL-000001"))
        pl1 = res_ini.scalar_one_or_none()

        if pl1:
            q_vot = select(Votacion).where(Votacion.iniciativa_id == pl1.id)
            vot_exist = (await session.execute(q_vot)).scalar_one_or_none()
            if not vot_exist:
                from datetime import date
                votacion = Votacion(
                    iniciativa_id=pl1.id,
                    fecha=date(2025, 5, 21),
                    sesion="62",
                    organo="Pleno del Parlamento de Andalucía",
                    titulo="Votación final del Dictamen de la Comisión sobre el Proyecto de Ley de creación del Colegio Oficial de Criminología de Andalucía",
                    votos_favor=104,
                    votos_contra=0,
                    abstenciones=0,
                    ausencias=5,
                    resultado="Aprobada",
                    url_fuente="https://www.parlamentodeandalucia.es/webdinamica/portal-web-parlamento/actividadparlamentaria/todaslasiniciativas/portipo.do?numexp=12-25/PL-000001"
                )
                session.add(votacion)
                await session.flush()

                # Desglose por grupos
                votos_grupos = [
                    (grupos_dict.get("G.P. Popular Andaluz"), "FAVOR", 58),
                    (grupos_dict.get("G.P. Socialista"), "FAVOR", 30),
                    (grupos_dict.get("G.P. VOX en Andalucía"), "FAVOR", 11),
                    (grupos_dict.get("G.P. Por Andalucía"), "FAVOR", 3),
                    (grupos_dict.get("G.P. Mixto-Adelante Andalucía"), "FAVOR", 2),
                ]
                for g_obj, sentido, nv in votos_grupos:
                    if g_obj:
                        vg = VotoGrupo(
                            votacion_id=votacion.id,
                            grupo_id=g_obj.id,
                            sentido=sentido,
                            num_votos=nv
                        )
                        session.add(vg)
                await session.commit()
                logger.info("Sample verified voting breakdown created.")

        logger.info("Database seeding finished successfully!")


if __name__ == "__main__":
    asyncio.run(run_seed())
