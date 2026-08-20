import datetime as dt
import re
from dataclasses import dataclass

_VERBOS_CREDITO = ("recebi", "ganhei", "entrou", "caiu", "depositei")

_VALOR_RE = re.compile(r"(\d+(?:[.,]\d{1,2})?)")
_STOPWORDS = {
    "gastei",
    "paguei",
    "comprei",
    "recebi",
    "ganhei",
    "entrou",
    "caiu",
    "depositei",
    "no",
    "na",
    "em",
    "de",
    "do",
    "da",
    "com",
    "reais",
    "real",
    "r$",
    "hoje",
    "ontem",
}


@dataclass
class MensagemParseada:
    valor: float
    descricao: str
    tipo: str  # debit | credit
    data: dt.date


class MensagemInvalida(Exception):
    pass


def parse_mensagem(texto: str, *, hoje: dt.date | None = None) -> MensagemParseada:
    hoje = hoje or dt.date.today()
    original = texto.strip()
    if not original:
        raise MensagemInvalida("Mensagem vazia.")

    minusculo = original.lower()

    match = _VALOR_RE.search(minusculo)
    if not match:
        raise MensagemInvalida(
            "Não encontrei um valor na mensagem. Ex: \"gastei 30 no uber hoje\"."
        )
    valor = float(match.group(1).replace(",", "."))

    tipo = "credit" if any(v in minusculo for v in _VERBOS_CREDITO) else "debit"

    data = hoje
    if "ontem" in minusculo:
        data = hoje - dt.timedelta(days=1)

    palavras = re.sub(r"[^\w\s,.]", " ", minusculo, flags=re.UNICODE).split()
    descricao_palavras = [
        p for p in palavras if p not in _STOPWORDS and not _VALOR_RE.fullmatch(p)
    ]
    descricao = " ".join(descricao_palavras).strip() or "Lançamento via Telegram"
    descricao = descricao[0].upper() + descricao[1:] if descricao else descricao

    return MensagemParseada(valor=valor, descricao=descricao, tipo=tipo, data=data)
