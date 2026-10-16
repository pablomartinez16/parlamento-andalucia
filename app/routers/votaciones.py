from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Votacion

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/votaciones", response_class=HTMLResponse)
async def listado_votaciones(request: Request, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Votacion)
        .options(
            selectinload(Votacion.iniciativa),
            selectinload(Votacion.desglose_grupos)
        )
        .order_by(desc(Votacion.fecha), desc(Votacion.id))
    )
    res = await db.execute(stmt)
    votaciones = res.scalars().all()

    return templates.TemplateResponse("votaciones.html", {
        "request": request,
        "votaciones": votaciones
    })
