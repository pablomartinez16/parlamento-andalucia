import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import engine, Base
from app.routers import iniciativas, votaciones
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized.")

    # Start background synchronization scheduler
    start_scheduler()
    
    yield
    
    # Shutdown
    stop_scheduler()
    await engine.dispose()
    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Aplicación cívica para la consulta abierta de la actividad legislativa del Parlamento de Andalucía",
    version="1.0.0",
    lifespan=lifespan
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include web routers
app.include_router(iniciativas.router)
app.include_router(votaciones.router)


@app.get("/health", tags=["Monitoring"])
async def healthcheck():
    """
    Healthcheck endpoint to monitor DB connectivity and app status.
    Used by Docker healthcheck and reverse proxies.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Healthcheck DB failure: {e}")
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "app": settings.APP_NAME,
        "database": db_status
    }
