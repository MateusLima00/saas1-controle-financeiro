"""Materialização de parcelas de compras parceladas.

Uma parcela criada em `POST /parcelamentos` é só um compromisso futuro —
não afeta saldo nem "gasto do mês" até a data de vencimento chegar. Este
job (rodado 1x/dia pelo scheduler, e também no startup da aplicação) vira
uma `Transaction` de verdade pra toda parcela com `data_vencimento <= hoje`
que ainda não tinha sido materializada (`transaction_id IS NULL`)."""
import logging

from sqlalchemy.orm import Session as DbSession

from .. import models
from ..timezone_utils import hoje as _hoje

logger = logging.getLogger(__name__)


def materializar_parcelas_vencidas(db: DbSession) -> int:
    hoje = _hoje()
    parcelas = (
        db.query(models.Parcela)
        .filter(models.Parcela.transaction_id.is_(None), models.Parcela.data_vencimento <= hoje)
        .all()
    )
    if not parcelas:
        return 0

    for parcela in parcelas:
        compra = parcela.compra
        transacao = models.Transaction(
            data=parcela.data_vencimento,
            descricao=f"{compra.descricao} ({parcela.numero}/{compra.num_parcelas})",
            categoria_id=compra.categoria_id,
            conta_id=compra.conta_id,
            valor=-abs(parcela.valor),
            tipo="debit",
            origem="parcelamento",
        )
        db.add(transacao)
        db.flush()  # garante transacao.id antes de linkar
        parcela.transaction_id = transacao.id

    db.commit()
    logger.info("Materializadas %d parcela(s) vencida(s).", len(parcelas))
    return len(parcelas)
