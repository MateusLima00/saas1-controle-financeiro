import datetime as dt
import logging
import secrets

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
    hash_password,
    verify_google_credential,
    verify_password,
)
from ..database import get_db
from ..rate_limit import checar_rate_limit, limpar_tentativas
from ..services.email_service import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

CODIGO_RECUPERACAO_TTL = dt.timedelta(minutes=15)


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
    return schemas.MeResponse(email=user.email, nome=user.nome)


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
    return schemas.MeResponse(email=user.email, nome=user.nome)


@router.post("/google", response_model=schemas.MeResponse)
def login_google(
    payload: schemas.GoogleLoginRequest, response: Response, db: DbSession = Depends(get_db)
):
    info = verify_google_credential(payload.credential)
    user = get_or_create_user(db, info["email"])
    create_session(db, user.id, response)
    return schemas.MeResponse(email=user.email, nome=user.nome)


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
    return schemas.MeResponse(email=current_user.email, nome=current_user.nome)


@router.put("/perfil", response_model=schemas.MeResponse)
def atualizar_perfil(
    payload: schemas.AtualizarPerfilRequest,
    current_user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    current_user.nome = payload.nome.strip()
    db.commit()
    return schemas.MeResponse(email=current_user.email, nome=current_user.nome)


@router.put("/senha")
def trocar_senha(
    payload: schemas.TrocarSenhaRequest,
    current_user: models.User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    """Troca a senha do usuário logado — exige a senha atual (evita que
    uma sessão roubada/deixada aberta troque a senha sem saber a antiga).
    Usuários que só têm login via Google (`hashed_password=""`) não têm
    senha atual pra confirmar; pedimos pra usarem sempre o Google nesse
    caso, em vez de aceitar qualquer coisa como "senha atual"."""
    if not current_user.hashed_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Essa conta usa login com Google e não tem senha própria pra trocar.",
        )
    if not verify_password(payload.senha_atual, current_user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha atual incorreta")

    current_user.hashed_password = hash_password(payload.senha_nova)
    db.commit()
    return {"ok": True}


@router.post("/recuperar-senha/solicitar")
def solicitar_recuperacao(
    payload: schemas.SolicitarRecuperacaoRequest, request: Request, db: DbSession = Depends(get_db)
):
    """Gera um código de 6 dígitos, válido por 15 min, e manda por email.
    Sempre responde {"ok": True} mesmo se o email não existir — não dá
    pra essa rota virar um oráculo de "esse email tem conta ou não"."""
    ip = request.client.host if request.client else "desconhecido"
    email_normalizado = payload.email.strip().lower()
    checar_rate_limit(f"recuperar:{ip}:{email_normalizado}", max_tentativas=3, janela_segundos=15 * 60)
    checar_rate_limit(f"recuperar:{ip}", max_tentativas=10, janela_segundos=60 * 60)

    user = db.query(models.User).filter(models.User.email == email_normalizado).first()
    if user and user.hashed_password:  # contas só-Google não têm senha pra recuperar
        codigo = f"{secrets.randbelow(1_000_000):06d}"
        db.add(
            models.PasswordResetCode(
                user_id=user.id,
                codigo=codigo,
                expires_at=dt.datetime.utcnow() + CODIGO_RECUPERACAO_TTL,
            )
        )
        db.commit()
        enviado = send_email(
            "Código para redefinir sua senha — Bolso Leve",
            f"Seu código é {codigo}. Ele expira em 15 minutos. Se você não pediu isso, ignore este email.",
            to=user.email,
        )
        if not enviado:
            logger.warning("Código de recuperação gerado mas email não enviado (SMTP não configurado?).")

    return {"ok": True}


@router.post("/recuperar-senha/confirmar", response_model=schemas.MeResponse)
def confirmar_recuperacao(
    payload: schemas.ConfirmarRecuperacaoRequest,
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
):
    ip = request.client.host if request.client else "desconhecido"
    email_normalizado = payload.email.strip().lower()
    # Código de 6 dígitos tem só 1 milhão de combinações — sem rate limit
    # apertado aqui, dava pra forçar por tentativa e erro dentro da janela
    # de 15 min de validade.
    checar_rate_limit(f"confirmar-recuperar:{ip}:{email_normalizado}", max_tentativas=8, janela_segundos=15 * 60)

    user = db.query(models.User).filter(models.User.email == email_normalizado).first()
    erro_generico = HTTPException(status.HTTP_400_BAD_REQUEST, "Código inválido ou expirado")
    if not user:
        raise erro_generico

    registro = (
        db.query(models.PasswordResetCode)
        .filter(
            models.PasswordResetCode.user_id == user.id,
            models.PasswordResetCode.codigo == payload.codigo.strip(),
            models.PasswordResetCode.usado == "",
        )
        .order_by(models.PasswordResetCode.id.desc())
        .first()
    )
    if not registro or registro.expires_at < dt.datetime.utcnow():
        raise erro_generico

    registro.usado = dt.datetime.utcnow().isoformat()
    user.hashed_password = hash_password(payload.senha_nova)
    db.commit()

    limpar_tentativas(f"confirmar-recuperar:{ip}:{email_normalizado}")
    create_session(db, user.id, response)
    return schemas.MeResponse(email=user.email, nome=user.nome)
