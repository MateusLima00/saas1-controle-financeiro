"""Popula o banco com os mesmos dados de src/data/mockData.js do frontend,
mais um usuário de login, pra comparar visualmente com o que já existe."""

import datetime as dt
import os

from . import models
from .auth import hash_password
from .database import Base, SessionLocal, engine, run_light_migrations


def _parse_data_br(data_str: str, ano: int = 2026) -> dt.date:
    dia, mes = data_str.split("/")
    return dt.date(ano, int(mes), int(dia))


def run():
    Base.metadata.create_all(bind=engine)
    run_light_migrations()
    db = SessionLocal()
    try:
        if db.query(models.User).first():
            print("Banco já populado, pulando seed.")
            return

        email = os.getenv("SEED_USER_EMAIL", "admin@example.com")
        senha = os.getenv("SEED_USER_PASSWORD", "troque-esta-senha")
        user = models.User(email=email, hashed_password=hash_password(senha))
        db.add(user)
        db.flush()  # garante user.id antes de referenciar em user_id abaixo
        uid = user.id

        categorias = {
            # -- Receitas (equivalente às linhas D7:D16 da planilha, por provedor) --
            "Renda": models.Category(
                nome="Renda", cor="var(--color-text-secondary)", regra="manual",
                grupo="receita", previsto=4200, provedor="Provedor 1", user_id=uid,
            ),
            # -- Gastos fixos (bloco 100 da planilha) --
            "Alimentação": models.Category(
                nome="Alimentação", cor="var(--color-cat-2)", regra='contém "ifood", "mercado"',
                grupo="fixo", previsto=600, user_id=uid,
            ),
            "Assinaturas": models.Category(
                nome="Assinaturas", cor="var(--color-cat-3)", regra='contém "netflix", "spotify"',
                grupo="fixo", previsto=80, user_id=uid,
            ),
            # -- Gastos passivos (bloco 400 da planilha) --
            "Transporte": models.Category(
                nome="Transporte", cor="var(--color-cat-1)", regra='contém "uber", "posto", "99"',
                grupo="passivo", previsto=250, user_id=uid,
            ),
            # -- Doações (bloco 300 da planilha) --
            "Dízimos e ofertas": models.Category(
                nome="Dízimos e ofertas", cor="var(--color-cat-6)", regra="manual",
                grupo="doacao", previsto=0, user_id=uid,
            ),
        }
        db.add_all(categorias.values())

        contas = [
            models.Account(banco="Nubank", tipo="checking", saldo=3200, status="connected", ultima_sync="há 4h", origem="manual", user_id=uid),
            models.Account(banco="Inter", tipo="savings", saldo=5220, status="connected", ultima_sync="há 4h", origem="manual", user_id=uid),
            models.Account(banco="C6 Bank", tipo="credit_card", saldo=-680, status="error", ultima_sync="há 2 dias", origem="manual", user_id=uid),
        ]
        db.add_all(contas)
        db.flush()

        transacoes = [
            ("03/08", "Uber", "Transporte", -32, "debit"),
            ("02/08", "iFood", "Alimentação", -58, "debit"),
            ("01/08", "Salário", "Renda", 4200, "credit"),
            ("31/07", "Netflix", "Assinaturas", -39.9, "debit"),
            ("30/07", "Posto Shell", "Transporte", -150, "debit"),
            ("29/07", "Mercado Extra", "Alimentação", -210, "debit"),
        ]
        for data_str, descricao, categoria_nome, valor, tipo in transacoes:
            db.add(
                models.Transaction(
                    data=_parse_data_br(data_str),
                    descricao=descricao,
                    categoria_id=categorias[categoria_nome].id,
                    valor=valor,
                    tipo=tipo,
                    origem="manual",
                    user_id=uid,
                )
            )

        metas = [
            (
                "Viagem para a China", "viagem", "Plane", "var(--color-cat-1)", 15000, 3200, "Dez/2026",
                [("01/06", 1000), ("01/07", 1200), ("01/08", 1000)],
            ),
            (
                "Reserva de emergência", "poupanca", "PiggyBank", "var(--color-cat-2)", 10000, 6200, None,
                [("01/07", 3000), ("01/08", 3200)],
            ),
            (
                "Notebook novo", "poupanca", "Laptop", "var(--color-cat-6)", 6000, 1400, "Mar/2027",
                [("01/08", 1400)],
            ),
        ]
        for nome, tipo, icone, cor, alvo, atual, prazo, historico in metas:
            goal = models.Goal(
                nome=nome, tipo=tipo, icone=icone, cor=cor,
                valor_alvo=alvo, valor_atual=atual, prazo=prazo, user_id=uid,
            )
            db.add(goal)
            db.flush()
            for data_str, valor in historico:
                db.add(models.GoalContribution(goal_id=goal.id, data=_parse_data_br(data_str), valor=valor))

        investimentos = [
            ("Tesouro Selic", "Renda fixa", "TrendingUp", "var(--color-cat-5)", 5000, 5320),
            ("Ações (carteira)", "Renda variável", "LineChart", "var(--color-cat-4)", 2000, 1840),
            ("CDB banco X", "Renda fixa", "Landmark", "var(--color-cat-2)", 3000, 3110),
        ]
        for nome, tipo, icone, cor, investido, atual in investimentos:
            db.add(models.Investment(nome=nome, tipo=tipo, icone=icone, cor=cor, valor_investido=investido, valor_atual=atual, user_id=uid))

        assinaturas = [
            ("Netflix", "Clapperboard", "var(--color-cat-3)", 39.9, "Mensal", "10/08"),
            ("Spotify", "Music", "var(--color-cat-2)", 21.9, "Mensal", "15/08"),
            ("iCloud 200GB", "Cloud", "var(--color-cat-5)", 12.9, "Mensal", "22/08"),
        ]
        for nome, icone, cor, valor, ciclo, proxima in assinaturas:
            db.add(models.Subscription(nome=nome, icone=icone, cor=cor, valor=valor, ciclo=ciclo, proxima_cobranca=proxima, user_id=uid))

        db.commit()
        print(f"Seed concluído. Usuário: {email} / senha: {senha}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
