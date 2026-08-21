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

    is_prod = os.getenv("DEBUG", "true").lower() != "true"
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
    após o login, e confere contra a allowlist de um único email (uso
    pessoal, sem multiusuário). Levanta HTTPException 401 se inválido, não
    verificado, ou fora da allowlist."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    allowed_email = os.getenv("ALLOWED_LOGIN_EMAIL", "")
    if not client_id or not allowed_email:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "Login com Google ainda não configurado (GOOGLE_CLIENT_ID/ALLOWED_LOGIN_EMAIL).",
        )

    try:
        info = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), client_id
        )
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token do Google inválido")

    if not info.get("email_verified"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email do Google não verificado")

    if info.get("email", "").lower() != allowed_email.lower():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email não autorizado")

    return info


def get_or_create_user(db: DbSession, email: str) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return user
    user = models.User(email=email, hashed_password="")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def require_service_token(authorization: str | None = Header(default=None)) -> None:
    """Auth pra integrações servidor-a-servidor (ex: Nero) — sem cookie de
    navegador, valida um token fixo via header `Authorization: Bearer <token>`."""
    esperado = os.getenv("NERO_INTEGRATION_TOKEN", "")
    recebido = (authorization or "").removeprefix("Bearer ").strip()
    if not esperado or not recebido or not hmac.compare_digest(recebido, esperado):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de integração inválido")


def require_meupluggy_refresh_token(authorization: str | None = Header(default=None)) -> None:
    """Mesmo padrão de `require_service_token`, token separado — chamado
    pelo serviço isolado `meupluggy-refresher` quando termina de atualizar
    as conexões no meu.pluggy.ai."""
    esperado = os.getenv("MEUPLUGGY_REFRESH_CALLBACK_TOKEN", "")
    recebido = (authorization or "").removeprefix("Bearer ").strip()
    if not esperado or not recebido or not hmac.compare_digest(recebido, esperado):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de integração inválido")
