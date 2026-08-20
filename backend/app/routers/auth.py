from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import (
    SESSION_COOKIE_NAME,
    create_session,
    destroy_session,
    get_current_user,
    get_or_create_user,
    verify_google_credential,
    verify_password,
)
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.MeResponse)
def login(payload: schemas.LoginRequest, response: Response, db: DbSession = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.senha, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou senha inválidos")

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
