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
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
