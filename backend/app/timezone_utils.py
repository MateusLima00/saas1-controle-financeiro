"""`dt.date.today()` usa o horário do servidor (Render roda em UTC) — a
partir de ~21h no horário de Brasília (UTC-3) o UTC já virou o dia
seguinte, então qualquer "hoje" calculado assim fica um dia adiantado
pro usuário (ex: última sync gravada com a data de amanhã). Use `hoje()`
em vez de `dt.date.today()` em qualquer lugar que represente o dia do
usuário (São Paulo), não do servidor."""
import datetime as dt
from zoneinfo import ZoneInfo

TZ_BRASIL = ZoneInfo("America/Sao_Paulo")


def hoje() -> dt.date:
    return dt.datetime.now(TZ_BRASIL).date()
