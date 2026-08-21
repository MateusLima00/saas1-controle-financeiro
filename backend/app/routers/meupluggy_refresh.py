"""Callback chamado pelo serviço isolado `meupluggy-refresher` (fora deste
repositório/deploy) quando termina de atualizar as conexões bancárias no
meu.pluggy.ai — dispara nosso sync de verdade na hora, em vez de esperar
o job de 20 min. Ver `meupluggy-refresher/README.md` pra explicação
completa de por que essa automação roda separada do backend principal
(a credencial mais sensível dela, senha de app do Gmail, nunca chega
perto deste processo)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from ..auth import require_meupluggy_refresh_token
from ..database import get_db
from ..services import pluggy_sync

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_meupluggy_refresh_token)],
)


@router.post("/meupluggy-refresh-callback")
def meupluggy_refresh_callback(db: DbSession = Depends(get_db)):
    resultados = pluggy_sync.sync_all_items(db)
    falhas = {iid: str(err) for iid, err in resultados.items() if err is not None}
    return {"itens_sincronizados": len(resultados), "falhas": falhas}
