"""Polling de desenvolvimento pro bot do Telegram.

Alternativa ao /telegram/webhook pra testar localmente sem expor a porta
8000 na internet (sem ngrok/domínio ainda). Usa getUpdates em long polling.
Rodar com: py -m app.telegram_poll

Em produção (com hospedagem definida), trocar por setWebhook apontando
pro /telegram/webhook e não usar mais este script.
"""

import os
import time

from dotenv import load_dotenv

load_dotenv()

from .database import SessionLocal  # noqa: E402
from .telegram_client import buscar_updates  # noqa: E402
from .telegram_service import handle_update  # noqa: E402


def main():
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("TELEGRAM_BOT_TOKEN não configurado no .env — abortando.")
        return

    print("Escutando mensagens do Telegram (Ctrl+C pra parar)...")
    offset = None
    while True:
        try:
            updates = buscar_updates(offset=offset)
        except Exception as exc:  # noqa: BLE001
            print(f"Erro ao buscar updates: {exc}")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            db = SessionLocal()
            try:
                handle_update(db, update)
            except Exception as exc:  # noqa: BLE001
                print(f"Erro processando update {update['update_id']}: {exc}")
            finally:
                db.close()


if __name__ == "__main__":
    main()
