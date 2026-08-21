"""Lógica de import de extrato compartilhada entre `/accounts/{id}/import`
(sessão de navegador) e `/integrations/nero/accounts/{id}/import` (token de
serviço, usado pelo Nero) — mesmo comportamento pelos dois caminhos."""
import datetime as dt

from fastapi import HTTPException
from sqlalchemy.orm import Session as DbSession

from .. import models, schemas
from ..categorization import categoria_para_descricao
from ..import_parsers import parse_csv, parse_ofx, parse_pdf
from ..timezone_utils import hoje


def importar_extrato(
    db: DbSession, account: models.Account, filename: str, conteudo: bytes
) -> schemas.ImportResultOut:
    nome = (filename or "").lower()

    try:
        if nome.endswith(".ofx") or nome.endswith(".qfx"):
            transacoes = parse_ofx(conteudo, account.id)
        elif nome.endswith(".csv"):
            transacoes = parse_csv(conteudo, account.id)
        elif nome.endswith(".pdf"):
            transacoes = parse_pdf(conteudo, account.id)
        else:
            raise HTTPException(
                400, "Formato não suportado. Envie um arquivo .csv, .ofx, .qfx ou .pdf."
            )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    ja_existentes = {
        row[0]
        for row in db.query(models.Transaction.external_id).filter(
            models.Transaction.external_id.in_([t.external_id for t in transacoes])
        )
    }
    # Também rastreia external_id repetido DENTRO do próprio arquivo (ex:
    # duas linhas idênticas de data+descrição+valor) — sem isso, a segunda
    # ocorrência só seria pega na query acima se a primeira já tivesse sido
    # commitada, o que não é garantido durante o mesmo import.
    vistos_neste_import: set[str] = set()

    importadas = 0
    duplicadas = 0
    for t in transacoes:
        if t.external_id in ja_existentes or t.external_id in vistos_neste_import:
            duplicadas += 1
            continue
        vistos_neste_import.add(t.external_id)
        categoria = categoria_para_descricao(db, t.descricao)
        db.add(
            models.Transaction(
                data=dt.date.fromisoformat(t.data),
                descricao=t.descricao,
                categoria_id=categoria.id if categoria else None,
                valor=t.valor,
                tipo=t.tipo,
                conta_id=account.id,
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
