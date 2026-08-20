import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
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
