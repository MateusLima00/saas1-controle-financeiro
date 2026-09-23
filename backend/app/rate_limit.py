"""Rate limit simples em memória (sem Redis/dependência externa) — suficiente
pra uma API que roda numa instância só (Render free tier). Se algum dia rodar
em múltiplas instâncias, isso precisa virar algo compartilhado (Redis), já
que cada processo teria sua própria contagem.

Usado em /auth/login e /auth/signup pra impedir brute force de senha e
enumeração de email sem limite de tentativas (o contador do Login.jsx é só
visual — isso aqui é o que de fato barra no servidor)."""
import threading
import time

from fastapi import HTTPException, status

_lock = threading.Lock()
# key -> lista de timestamps (epoch) das tentativas dentro da janela atual
_tentativas: dict[str, list[float]] = {}


def checar_rate_limit(chave: str, *, max_tentativas: int, janela_segundos: int) -> None:
    """Levanta 429 se `chave` já teve `max_tentativas` ou mais dentro dos
    últimos `janela_segundos`. Cada chamada conta como uma tentativa nova."""
    agora = time.time()
    corte = agora - janela_segundos

    with _lock:
        tentativas = [t for t in _tentativas.get(chave, []) if t > corte]
        if len(tentativas) >= max_tentativas:
            _tentativas[chave] = tentativas
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Muitas tentativas. Aguarde um pouco antes de tentar de novo.",
            )
        tentativas.append(agora)
        _tentativas[chave] = tentativas


def limpar_tentativas(chave: str) -> None:
    """Chamado em login bem-sucedido — reseta o contador dessa chave pra não
    penalizar o próximo login legítimo por causa de erros de digitação
    antigos."""
    with _lock:
        _tentativas.pop(chave, None)
