import datetime as dt
import hmac
import os
import secrets

from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from passlib.context import CryptContext
from sqlalchemy.orm import Session as DbSession

from . import models
from .database import get_db

SESSION_COOKIE_NAME = "session_token"
SESSION_TTL = dt.timedelta(days=7)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    # Usuários criados via Google (get_or_create_user) têm hashed_password
    # "" (sem senha) — passlib levanta exceção ao verificar contra um hash
    # vazio/inválido em vez de simplesmente retornar False, então sem essa
    # checagem um login por senha nessas contas derrubaria a rota com 500
    # em vez de um 401 normal.
    if not hashed:
        return False
    return pwd_context.verify(password, hashed)


def create_session(db: DbSession, user_id: int, response: Response) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = dt.datetime.utcnow() + SESSION_TTL
    db.add(models.Session(token=token, user_id=user_id, expires_at=expires_at))
    db.commit()

    # Default SEGURO: se DEBUG não estiver setado no ambiente, assume
    # produção (cookie Secure). Antes o default era "true" (modo dev
    # inseguro) — um ambiente que esquecesse de definir DEBUG=false caía
    # silenciosamente em cookie não-Secure. Agora é o oposto: só vira dev
    # se alguém setar DEBUG=true explicitamente (é isso que o
    # .env.example já faz pra ambiente local).
    is_prod = os.getenv("DEBUG", "false").lower() != "true"
    # Em produção, frontend e backend ficam em subdomínios *.onrender.com
    # diferentes — onrender.com está na Public Suffix List (como
    # github.io/vercel.app), então o navegador trata cada subdomínio como
    # um site diferente. "SameSite=Lax" bloqueia o cookie em requisições
    # cross-site via fetch/XHR (só permite navegação de página inteira),
    # então precisa de "None" (que por sua vez exige Secure=True) pra
    # cookie ir junto nas chamadas da API. Em dev local, front e back
    # ficam ambos em "localhost" (mesmo site, portas diferentes não
    # importam pra SameSite) — "Lax" já basta e evita exigir HTTPS local.
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="none" if is_prod else "lax",
        secure=is_prod,
        max_age=int(SESSION_TTL.total_seconds()),
        path="/",
    )
    return token


def destroy_session(db: DbSession, token: str | None, response: Response) -> None:
    if token:
        db.query(models.Session).filter(models.Session.token == token).delete()
        db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: DbSession = Depends(get_db),
) -> models.User:
    if not session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")

    session = (
        db.query(models.Session)
        .filter(models.Session.token == session_token)
        .first()
    )
    if not session or session.expires_at < dt.datetime.utcnow():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada")

    user = db.query(models.User).filter(models.User.id == session.user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")

    return user


def verify_google_credential(credential: str) -> dict:
    """Valida o ID token que o Google Identity Services manda pro frontend
    após o login. Aberto pra qualquer conta Google com email verificado —
    igual ao signup por email/senha, cada conta nova nasce com dados
    isolados (ver create_user_with_password / get_or_create_user).
    Levanta HTTPException 401 se o token for inválido ou não verificado."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Login com Google ainda não configurado (GOOGLE_CLIENT_ID).",
        )

    try:
        info = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), client_id
        )
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token do Google inválido")

    if not info.get("email_verified"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email do Google não verificado")

    return info


def create_user_with_password(db: DbSession, email: str, senha: str) -> models.User:
    """Cria uma conta nova via email/senha (signup). Cada usuário tem seus
    próprios dados isolados (contas, transações, categorias, metas...) —
    ver `user_id` em models.py e o filtro por `current_user.id` em cada
    router. Levanta HTTPException 409 se o email já estiver cadastrado."""
    email_normalizado = email.strip().lower()
    existente = db.query(models.User).filter(models.User.email == email_normalizado).first()
    if existente:
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe uma conta com esse email")

    user = models.User(email=email_normalizado, hashed_password=hash_password(senha))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_user(db: DbSession, email: str) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return user
    user = models.User(email=email, hashed_password="")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_owner_user_id(db: DbSession) -> int | None:
    """Retorna o id do usuário "dono" original (o primeiro criado) —
    usado por integrações sem sessão de navegador que não têm como saber
    "qual usuário" (bot do Telegram, integração Nero, jobs em background
    do scheduler). Essas integrações são pessoais/de uso próprio e devem
    continuar operando sempre sobre os dados do dono, mesmo depois que
    outras pessoas criarem conta própria no app."""
    user = db.query(models.User).order_by(models.User.id).first()
    return user.id if user else None


def require_ajax_header(x_requested_with: str | None = Header(default=None)) -> None:
    """Exige um header custom (não enviável por um <form> HTML puro) em
    endpoints multipart/form-data autenticados por cookie de sessão.

    O motivo: multipart/form-data é um dos content-types "simples" do
    CORS — o navegador manda a requisição SEM preflight, então nosso
    `CORSMiddleware` (que só libera `FRONTEND_ORIGIN`) nunca chega a
    bloquear nada. Um site malicioso poderia então montar um <form
    method="post" enctype="multipart/form-data"> escondido apontando pro
    nosso backend, e o navegador anexaria o cookie de sessão da vítima
    (SameSite=None em produção) sozinho — CSRF clássico via upload.
    Exigir este header força o navegador a tratar a requisição como
    "não-simples" e rodar o preflight de CORS antes, que aí sim barra
    origem não autorizada — e um <form> HTML comum não consegue setar
    headers customizados, só JavaScript (que já respeita CORS)."""
    if x_requested_with != "fetch":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Requisição não autorizada")


def require_service_token(authorization: str | None = Header(default=None)) -> None:
    """Auth pra integrações servidor-a-servidor (ex: Nero) — sem cookie de
    navegador, valida um token fixo via header `Authorization: Bearer <token>`."""
    esperado = os.getenv("NERO_INTEGRATION_TOKEN", "")
    recebido = (authorization or "").removeprefix("Bearer ").strip()
    if not esperado or not recebido or not hmac.compare_digest(recebido, esperado):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de integração inválido")


