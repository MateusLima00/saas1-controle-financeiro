"""Status de assinatura (ativa x contrato encerrado) — usado tanto na
listagem (`routers/subscriptions.py`) quanto nos lembretes/notificações
(`services/notifications.py`, `routers/dashboard.py`), pra manter a
mesma regra em todo lugar: uma assinatura sem `duracao_meses` é mensal
indefinida (sempre ativa); com `duracao_meses` setado, ela só é ativa até
`data_inicio + duracao_meses` meses — depois disso some sozinha das
listas de ativas e dos lembretes, sem precisar apagar na mão."""
import calendar
import datetime as dt

from . import models


def _somar_meses(data: dt.date, meses: int) -> dt.date:
    """Mesma lógica de routers/parcelamentos.py: crava no último dia do
    mês de destino se o dia original não existir nele."""
    mes_total = data.month - 1 + meses
    ano = data.year + mes_total // 12
    mes = mes_total % 12 + 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return dt.date(ano, mes, dia)


def data_fim_contrato(assinatura: "models.Subscription") -> dt.date | None:
    """Retorna a data em que o contrato termina, ou None se for uma
    assinatura mensal sem prazo fixo."""
    if not assinatura.duracao_meses:
        return None
    inicio = assinatura.data_inicio or dt.date.today()
    return _somar_meses(inicio, assinatura.duracao_meses)


def assinatura_ativa(assinatura: "models.Subscription", hoje: dt.date) -> bool:
    fim = data_fim_contrato(assinatura)
    return fim is None or hoje <= fim
