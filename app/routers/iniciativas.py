from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Iniciativa, Legislatura, Tramite, Documento, Votacion, VotoGrupo

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def inicio(request: Request, db: AsyncSession = Depends(get_db)):
    # Stats
    total_iniciativas = await db.scalar(select(func.count(Iniciativa.id))) or 0
    total_leyes = await db.scalar(
        select(func.count(Iniciativa.id)).where(
            or_(
                Iniciativa.tipo.ilike("%ley%"),
                Iniciativa.tipo.ilike("%proyecto%")
            )
        )
    ) or 0
    total_votaciones = await db.scalar(select(func.count(Votacion.id))) or 0

    # Recent 6 initiatives
    stmt = (
        select(Iniciativa)
        .order_by(desc(Iniciativa.created_at))
        .limit(6)
    )
    res = await db.execute(stmt)
    ultimas = res.scalars().all()

    return templates.TemplateResponse("inicio.html", {
        "request": request,
        "stats": {
            "total_iniciativas": total_iniciativas,
            "total_leyes": total_leyes,
            "total_votaciones": total_votaciones
        },
        "ultimas": ultimas
    })


@router.get("/iniciativas", response_class=HTMLResponse)
async def listado_iniciativas(
    request: Request,
    q: str = Query(None),
    tipo: str = Query(None),
    estado: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = 15,
    db: AsyncSession = Depends(get_db)
):
    query = select(Iniciativa)

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(
            or_(
                Iniciativa.titulo.ilike(term),
                Iniciativa.expediente.ilike(term),
                Iniciativa.extracto.ilike(term),
                Iniciativa.proponente.ilike(term)
            )
        )

    if tipo and tipo.strip():
        query = query.where(Iniciativa.tipo == tipo.strip())

    if estado and estado.strip():
        query = query.where(Iniciativa.estado == estado.strip())

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_stmt) or 0

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Iniciativa.fecha_creacion), desc(Iniciativa.id)).offset(offset).limit(page_size)
    res = await db.execute(query)
    iniciativas = res.scalars().all()

    # Get distinct tipos and estados for filter dropdowns
    tipos_res = await db.execute(select(Iniciativa.tipo).distinct().where(Iniciativa.tipo.isnot(None)))
    tipos_disponibles = sorted([t[0] for t in tipos_res.fetchall() if t[0]])

    estados_res = await db.execute(select(Iniciativa.estado).distinct().where(Iniciativa.estado.isnot(None)))
    estados_disponibles = sorted([e[0] for e in estados_res.fetchall() if e[0]])

    total_pages = (total + page_size - 1) // page_size or 1

    return templates.TemplateResponse("listado.html", {
        "request": request,
        "iniciativas": iniciativas,
        "total": total,
        "current_page": page,
        "total_pages": total_pages,
        "filters": {"q": q, "tipo": tipo, "estado": estado},
        "tipos_disponibles": tipos_disponibles,
        "estados_disponibles": estados_disponibles
    })


@router.get("/iniciativa/{expediente:path}", response_class=HTMLResponse)
async def detalle_iniciativa(
    expediente: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Iniciativa)
        .where(Iniciativa.expediente == expediente)
        .options(
            selectinload(Iniciativa.legislatura),
            selectinload(Iniciativa.tramites),
            selectinload(Iniciativa.documentos),
            selectinload(Iniciativa.votaciones).selectinload(Votacion.desglose_grupos).selectinload(VotoGrupo.grupo)
        )
    )
    res = await db.execute(stmt)
    iniciativa = res.scalar_one_or_none()

    if not iniciativa:
        raise HTTPException(status_code=404, detail=f"Iniciativa con expediente {expediente} no encontrada.")

    return templates.TemplateResponse("detalle.html", {
        "request": request,
        "iniciativa": iniciativa
    })


@router.get("/acerca-de", response_class=HTMLResponse)
async def acerca_de(request: Request):
    return templates.TemplateResponse("legal.html", {"request": request})
