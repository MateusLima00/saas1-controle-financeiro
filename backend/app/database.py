import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Carregado aqui (não só em main.py) porque scripts standalone como
# `python -m app.seed` importam este módulo sem passar por main.py antes —
# sem isso, DATABASE_URL (e qualquer outra env var) nunca são lidas do
# .env nesses scripts, e tudo cai silenciosamente no SQLite default.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./controle_financeiro.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
# pool_pre_ping: testa a conexão com um SELECT 1 antes de cada uso e
# reconecta se estiver morta. Necessário com Neon (Postgres serverless) -
# ele suspende a instância de computação após período ocioso e mata as
# conexões abertas; sem isso, sessões antigas (ex: mantidas vivas por
# jobs em background como o scheduler) quebram com
# "AdminShutdown: terminating connection due to administrator command".
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_light_migrations():
    """`Base.metadata.create_all` só cria tabelas que não existem ainda —
    não adiciona coluna nova a uma tabela já criada num banco antigo. Como
    o projeto não usa Alembic, aplicamos aqui ALTER TABLE ADD COLUMN
    idempotentes. Roda toda subida; se a coluna já existe, pula.
    """
    inspector = inspect(engine)
    tabelas_existentes = set(inspector.get_table_names())
    if not tabelas_existentes:
        return  # banco ainda nem existe — create_all cuida de tudo do zero

    if "categories" in tabelas_existentes:
        colunas_existentes = {col["name"] for col in inspector.get_columns("categories")}
        novas_colunas = {
            "grupo": "VARCHAR DEFAULT 'fixo'",
            "previsto": "FLOAT DEFAULT 0",
            "provedor": "VARCHAR",
        }
        with engine.begin() as conn:
            for nome, definicao in novas_colunas.items():
                if nome not in colunas_existentes:
                    conn.execute(text(f"ALTER TABLE categories ADD COLUMN {nome} {definicao}"))

    if "subscriptions" in tabelas_existentes:
        colunas_existentes = {col["name"] for col in inspector.get_columns("subscriptions")}
        novas_colunas = {
            "data_inicio": "DATE DEFAULT CURRENT_DATE",
            "duracao_meses": "INTEGER",
        }
        with engine.begin() as conn:
            for nome, definicao in novas_colunas.items():
                if nome not in colunas_existentes:
                    conn.execute(text(f"ALTER TABLE subscriptions ADD COLUMN {nome} {definicao}"))

    # -- Multi-tenant: adiciona user_id em toda tabela de dado do usuário,
    # e faz o backfill pro primeiro usuário existente (o dono original dos
    # dados, antes de existir signup) — assim nenhuma linha antiga fica
    # órfã nem vira visível pra uma conta nova.
    tabelas_com_user_id = [
        "accounts", "categories", "transactions", "goals", "investments",
        "subscriptions", "compras_parceladas",
    ]
    with engine.begin() as conn:
        primeiro_usuario = conn.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
        for tabela in tabelas_com_user_id:
            if tabela not in tabelas_existentes:
                continue
            colunas = {col["name"] for col in inspector.get_columns(tabela)}
            if "user_id" not in colunas:
                conn.execute(text(f"ALTER TABLE {tabela} ADD COLUMN user_id INTEGER"))
            if primeiro_usuario is not None:
                conn.execute(
                    text(f"UPDATE {tabela} SET user_id = :uid WHERE user_id IS NULL"),
                    {"uid": primeiro_usuario},
                )
