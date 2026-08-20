import re

from sqlalchemy.orm import Session as DbSession

from . import models

_REGRA_RE = re.compile(r'"([^"]+)"')


def categoria_para_descricao(db: DbSession, descricao: str) -> models.Category | None:
    descricao_lower = descricao.lower()
    for categoria in db.query(models.Category).all():
        palavras_chave = _REGRA_RE.findall(categoria.regra or "")
        if any(p.lower() in descricao_lower for p in palavras_chave):
            return categoria
    return None
