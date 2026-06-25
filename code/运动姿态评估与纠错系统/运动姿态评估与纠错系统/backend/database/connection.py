from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

connect_args = {}
if settings.DB_TYPE == 'sqlite':
    connect_args['check_same_thread'] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_size=10 if settings.DB_TYPE != 'sqlite' else None,
    max_overflow=20 if settings.DB_TYPE != 'sqlite' else None,
    pool_recycle=3600 if settings.DB_TYPE != 'sqlite' else None,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
