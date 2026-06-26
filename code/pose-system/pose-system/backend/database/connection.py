from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

connect_args = {}
if settings.DB_TYPE == 'sqlite':
    connect_args['check_same_thread'] = False

engine_kwargs = {
    'connect_args': connect_args,
}
if settings.DB_TYPE != 'sqlite':
    engine_kwargs['pool_size'] = 10
    engine_kwargs['max_overflow'] = 20
    engine_kwargs['pool_recycle'] = 3600

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
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
