from sqlalchemy import create_engine, inspect, text
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


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table."""
    insp = inspect(engine)
    cols = {c['name'] for c in insp.get_columns(table_name)}
    return column_name in cols


def _table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    insp = inspect(engine)
    return table_name in insp.get_table_names()


def run_migrations():
    """
    Add missing columns to existing tables.
    Uses raw ALTER TABLE so it works with both MySQL and SQLite.
    Only adds columns that don't already exist.
    """
    # ── action_library new columns ──
    new_cols = {
        'steps': 'TEXT',
        'cues': 'TEXT',
        'contraindications': 'TEXT',
        'family': 'VARCHAR(100)',
        'family_name': 'VARCHAR(200)',
        'is_custom': 'BOOLEAN DEFAULT FALSE',
        'created_by': 'INTEGER',
        'updated_at': 'DATETIME',
    }
    for col, col_type in new_cols.items():
        if _table_exists('action_library') and not _column_exists('action_library', col):
            with engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE action_library ADD COLUMN {col} {col_type}'))
                conn.commit()

    # ── user new columns ──
    user_cols = {
        'last_login_at': 'DATETIME',
        'last_active_at': 'DATETIME',
        'deleted_at': 'DATETIME',
    }
    for col, col_type in user_cols.items():
        if _table_exists('user') and not _column_exists('user', col):
            with engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE user ADD COLUMN {col} {col_type}'))
                conn.commit()


def init_db():
    # 确保所有模型被导入，SQLAlchemy 才能发现并创建表
    from backend.database import models  # noqa: F401
    from backend.database import models_v2  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 添加后续新增的列（create_all 只建表不修改已有表）
    run_migrations()
