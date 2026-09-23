from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie, status
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import (
    SESSION_COOKIE_NAME,
    create_session,
    create_user_with_password,
    destroy_session,
    get_current_user,
    get_or_create_user,
    verify_google_credential,
    verify_password,
)
from ..database import get_db
from ..rate_limit import checar_rate_limit, limpar_tentativas

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.MeResponse)
def login(payload: schemas.LoginRequest, request: Request, response: Response, db: DbSession = Depends(get_db)):
    ip = request.client.host if request.client else "desconhecido"
    email_normalizado = payload.email.strip().lower()
    # Duas chaves: por IP+email (trava tentativas repetidas numa conta
    # específica) e por IP sozinho (trava spray de senha em várias contas
    # a partir do mesmo IP) — sem isso, um brute force que troca de email
    # a cada tentativa escaparia do limite por conta.
    checar_rate_limit(f"login:{ip}:{email_normalizado}", max_tentativas=5, janela_segundos=15 * 60)
    checar_rate_limit(f"login:{ip}", max_tentativas=20, janela_segundos=15 * 60)

    user = db.query(models.User).filter(models.User.email == email_normalizado).first()
    if not user or not verify_password(payload.senha, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou senha inválidos")

    limpar_tentativas(f"login:{ip}:{email_normalizado}")
    create_session(db, user.id, response)
    return schemas.MeResponse(email=user.email)


@router.post("/signup", response_model=schemas.MeResponse, status_code=201)
def signup(payload: schemas.SignupRequest, request: Request, response: Response, db: DbSession = Depends(get_db)):
    """Cria uma conta nova (email + senha). Cada conta começa com um
    espaço de dados vazio e isolado — nada é compartilhado entre
    usuários (ver `create_user_with_password`)."""
    ip = request.client.host if request.client else "desconhecido"
    # Limite mais apertado que o login: signup é usado principalmente por
    # gente de verdade criando 1 conta, então tentativas em excesso do
    # mesmo IP são quase sempre enumeração de email (checar quais já
    # existem via o 409) ou spam de criação de conta.
    checar_rate_limit(f"signup:{ip}", max_tentativas=8, janela_segundos=60 * 60)

    user = create_user_with_password(db, payload.email, payload.senha)
    create_session(db, user.id, response)
    return schemas.MeResponse(email=user.email)


@router.post("/google", response_model=schemas.MeResponse)
def login_google(
    payload: schemas.GoogleLoginRequest, response: Response, db: DbSession = Depends(get_db)
):
    info = verify_google_credential(payload.credential)
    user = get_or_create_user(db, info["email"])
    create_session(db, user.id, response)
    return schemas.MeResponse(email=user.email)


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: DbSession = Depends(get_db),
):
    destroy_session(db, session_token, response)
    return {"ok": True}


@router.get("/me", response_model=schemas.MeResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return schemas.MeResponse(email=current_user.email)
