from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Base de onde os modelos SQLAlchemy irão herdar
Base = declarative_base()

# Evita quebrar a aplicação caso a DATABASE_URL ainda não esteja configurada no .env inicial
if settings.DATABASE_URL:
    # Ajuste para SQLite funcionar corretamente com a mesma engine
    connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
    
    # Remove configurações de pool se for SQLite
    if settings.DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args=connect_args
        )
    else:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True, # Garante que conexões inativas/quebradas sejam descartadas antes do uso
            pool_size=10,       # Gerenciamento de pool (Performance)
            max_overflow=20
        )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None

def get_db():
    """
    Dependency Injection para FastAPI.
    Garante a abertura e o fechamento correto da sessão com o banco de dados.
    """
    if SessionLocal is None:
        raise Exception("DATABASE_URL não configurada no ambiente.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
