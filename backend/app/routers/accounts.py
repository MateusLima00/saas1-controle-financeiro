import datetime as dt
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..import_parsers import parse_csv, parse_ofx
from ..services import pluggy_client, pluggy_sync
from ..timezone_utils import hoje

router = APIRouter(
    prefix="/accounts", tags=["accounts"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[schemas.AccountOut])
def list_accounts(db: DbSession = Depends(get_db)):
    return db.query(models.Account).all()


@router.post("", response_model=schemas.AccountOut, status_code=201)
def create_account(payload: schemas.AccountCreate, db: DbSession = Depends(get_db)):
    account = models.Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=schemas.AccountOut)
def update_account(account_id: int, payload: schemas.AccountUpdate, db: DbSession = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Conta não encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: DbSession = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Conta não encontrada")

    item_id = account.pluggy_item_id
    db.delete(account)
    db.commit()

    if item_id:
        outras_contas_do_item = (
            db.query(models.Account).filter(models.Account.pluggy_item_id == item_id).count()
        )
        if outras_contas_do_item == 0:
            try:
                pluggy_client.delete_item(item_id)
            except pluggy_client.PluggyError:
                # Item já pode ter sido removido do lado da Pluggy, ou a API
                # está fora do ar — a exclusão local já aconteceu, então não
                # bloqueamos o usuário por isso.
                pass


def _require_pluggy_configurado():
    if not (os.getenv("PLUGGY_CLIENT_ID") and os.getenv("PLUGGY_CLIENT_SECRET")):
        raise HTTPException(
            501,
            "Integração com a Pluggy ainda não configurada (faltam PLUGGY_CLIENT_ID/"
            "PLUGGY_CLIENT_SECRET). Use o import manual de CSV/OFX por enquanto.",
        )


@router.post("/connect-token", response_model=schemas.ConnectTokenOut)
def create_connect_token(payload: schemas.SyncRequest | None = None):
    """Gera o token de curta duração usado pelo Pluggy Connect Widget no
    frontend (tela Contas). O Conector 200 (MeuPluggy) é OAuth — a conexão
    de verdade com o banco só acontece nesse widget, no navegador do
    usuário; o backend não tem como automatizar login/consentimento."""
    _require_pluggy_configurado()
    try:
        token = pluggy_client.create_connect_token(payload.item_id if payload else None)
    except pluggy_client.PluggyError as exc:
        raise HTTPException(502, f"Falha ao gerar connect token da Pluggy: {exc}")
    return schemas.ConnectTokenOut(connect_token=token)


@router.post("/sync", response_model=schemas.SyncResultOut)
def sync_accounts(payload: schemas.SyncRequest | None = None, db: DbSession = Depends(get_db)):
    """Busca contas/transações na Pluggy e faz upsert local.

    - Se `itemId` for passado no corpo, é porque o Pluggy Connect Widget
      acabou de conectar um banco novo (ou re-autenticar um existente) —
      sincroniza só esse item.
    - Sem `itemId` (clique em "atualizar agora" na tela Contas), sincroniza
      TODOS os itens já conectados — não só o primeiro que aparecer, senão
      quem tem mais de um banco conectado nunca vê os outros atualizarem.
    - Sem nenhum item conectado ainda, orienta a conectar via widget
      primeiro (endpoint `/accounts/connect-token`)."""
    _require_pluggy_configurado()

    item_id = payload.item_id if payload else None
    if item_id:
        try:
            contas_atualizadas = pluggy_sync.sync_item(db, item_id)
            db.commit()
        except pluggy_client.PluggyError as exc:
            db.rollback()
            raise HTTPException(502, f"Falha ao sincronizar com a Pluggy: {exc}")
        return schemas.SyncResultOut(
            status="ok",
            mensagem=f"{contas_atualizadas} conta(s) sincronizada(s) via Pluggy.",
            contas_atualizadas=contas_atualizadas,
        )

    item_ids = pluggy_sync.distinct_item_ids(db)
    if not item_ids:
        raise HTTPException(
            400,
            "Nenhuma conta conectada à Pluggy ainda. Conecte um banco pelo "
            "Pluggy Connect Widget (GET connect-token) antes de sincronizar.",
        )

    resultados = pluggy_sync.sync_all_items(db)
    falhas = {iid: err for iid, err in resultados.items() if err is not None}
    contas_atualizadas = (
        db.query(models.Account).filter(models.Account.pluggy_item_id.in_(item_ids)).count()
    )
    if falhas and len(falhas) == len(resultados):
        primeiro_erro = next(iter(falhas.values()))
        raise HTTPException(502, f"Falha ao sincronizar com a Pluggy: {primeiro_erro}")

    mensagem = f"{contas_atualizadas} conta(s) sincronizada(s) via Pluggy ({len(item_ids)} banco(s))."
    if falhas:
        mensagem += f" {len(falhas)} banco(s) falharam e serão tentados de novo automaticamente."

    return schemas.SyncResultOut(
        status="ok" if not falhas else "parcial",
        mensagem=mensagem,
        contas_atualizadas=contas_atualizadas,
    )


@router.post("/{account_id}/import", response_model=schemas.ImportResultOut)
async def import_extrato(account_id: int, file: UploadFile, db: DbSession = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Conta não encontrada")

    nome = (file.filename or "").lower()
    conteudo = await file.read()

    try:
        if nome.endswith(".ofx") or nome.endswith(".qfx"):
            transacoes = parse_ofx(conteudo, account_id)
        elif nome.endswith(".csv"):
            transacoes = parse_csv(conteudo, account_id)
        else:
            raise HTTPException(400, "Formato não suportado. Envie um arquivo .csv, .ofx ou .qfx.")
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    importadas = 0
    duplicadas = 0
    for t in transacoes:
        existente = (
            db.query(models.Transaction)
            .filter(models.Transaction.external_id == t.external_id)
            .first()
        )
        if existente:
            duplicadas += 1
            continue
        db.add(
            models.Transaction(
                data=dt.date.fromisoformat(t.data),
                descricao=t.descricao,
                valor=t.valor,
                tipo=t.tipo,
                conta_id=account_id,
                origem="import",
                external_id=t.external_id,
            )
        )
        importadas += 1

    account.ultima_sync = hoje().isoformat()
    db.commit()

    return schemas.ImportResultOut(
        importadas=importadas,
        duplicadas=duplicadas,
        ignoradas=len(transacoes) - importadas - duplicadas,
    )
