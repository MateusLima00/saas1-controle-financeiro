from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DbSession

from ..database import get_db
from ..telegram_service import handle_update

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def webhook(request: Request, db: DbSession = Depends(get_db)):
    payload = await request.json()
    handle_update(db, payload)
    return {"ok": True}
