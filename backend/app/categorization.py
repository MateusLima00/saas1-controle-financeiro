import re

from sqlalchemy.orm import Session as DbSession

from . import models

_REGRA_RE = re.compile(r'"([^"]+)"')

# Termos de boilerplate bancário que não identificam a transação em si (o
# "quem"/"o quê") — removidos antes de extrair a palavra-chave pra
# aprendizado automático de categoria, senão toda correção manual criaria
# uma regra genérica tipo "pix enviado" que bate em quase tudo.
_BOILERPLATE_RE = re.compile(
    r'"?cp\s*:\s*\d+-|pix\s+(enviado|recebido)|compra\s+no\s+(d[ée]bito|cr[ée]dito)|'
    r"pagamento\s+realizado|com\s+saldo|fatura|:|\"",
    re.IGNORECASE,
)


def categoria_para_descricao(db: DbSession, descricao: str, user_id: int) -> models.Category | None:
    descricao_lower = descricao.lower()
    categorias = db.query(models.Category).filter(models.Category.user_id == user_id).all()
    for categoria in categorias:
        palavras_chave = _REGRA_RE.findall(categoria.regra or "")
        if any(p.lower() in descricao_lower for p in palavras_chave):
            return categoria
    return None


def extrair_palavra_chave(descricao: str) -> str:
    """Tira o boilerplate bancário ('Pix enviado', 'Cp :12345-', 'Com
    saldo' etc.) da descrição, deixando só o que de fato identifica quem
    recebeu/pagou — usado pra aprender uma regra nova quando o usuário
    corrige a categoria manualmente. Se sobrar pouca coisa (descrição já
    era só boilerplate), usa a descrição original mesmo."""
    limpa = _BOILERPLATE_RE.sub(" ", descricao)
    limpa = re.sub(r"\s*-\s*", " ", limpa)
    limpa = re.sub(r"\s+", " ", limpa).strip(" -")
    return limpa if len(limpa) >= 3 else descricao.strip()


def aprender_regra(db: DbSession, categoria: models.Category, descricao: str) -> None:
    """Registra a palavra-chave extraída de `descricao` na regra da
    categoria, se ainda não estiver lá — pra próxima transação parecida
    cair categorizada sozinha. Nunca aprende de descrições genéricas
    demais (ex: só "Pix enviado" sem contraparte identificável)."""
    palavra_chave = extrair_palavra_chave(descricao)
    if len(palavra_chave) < 3:
        return
    palavras_existentes = {p.lower() for p in _REGRA_RE.findall(categoria.regra or "")}
    if palavra_chave.lower() in palavras_existentes:
        return
    categoria.regra = f'{categoria.regra}, "{palavra_chave}"' if categoria.regra else f'contém "{palavra_chave}"'
