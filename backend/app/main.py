import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from . import models, scheduler
from .database import Base, engine, run_light_migrations
from .routers import (
    accounts,
    auth,
    categories,
    dashboard,
    goals,
    integrations,
    investments,
    parcelamentos,
    subscriptions,
    telegram,
    transactions,
)

Base.metadata.create_all(bind=engine)
run_light_migrations()

app = FastAPI(title="Controle Financeiro API")

frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _security_headers(request, call_next):
    """Headers de segurança básicos que o FastAPI/Starlette não manda por
    padrão — API pura (sem HTML renderizado aqui), então o foco é impedir
    que o navegador tente "adivinhar" um content-type diferente do que a
    API declarou (`nosniff`) e bloquear a API de ser carregada dentro de
    um <iframe> de outro site (`X-Frame-Options`), que não tem nenhum uso
    legítimo aqui."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(goals.router)
app.include_router(investments.router)
app.include_router(subscriptions.router)
app.include_router(dashboard.router)
app.include_router(telegram.router)
app.include_router(integrations.router)
app.include_router(parcelamentos.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def _iniciar_scheduler():
    scheduler.start()
    scheduler.materializar_parcelas_na_subida()


@app.on_event("shutdown")
def _parar_scheduler():
    scheduler.stop()
