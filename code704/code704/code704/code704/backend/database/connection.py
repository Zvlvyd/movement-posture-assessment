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
        'token_version': 'INTEGER DEFAULT 0',
        'last_login_at': 'DATETIME',
        'last_active_at': 'DATETIME',
        'deleted_at': 'DATETIME',
    }
    for col, col_type in user_cols.items():
        if _table_exists('user') and not _column_exists('user', col):
            with engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE user ADD COLUMN {col} {col_type}'))
                conn.commit()

    # ── action_library: is_visible column ──
    if _table_exists('action_library') and not _column_exists('action_library', 'is_visible'):
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE action_library ADD COLUMN is_visible BOOLEAN DEFAULT 1'))
            conn.commit()

    # ── class_group: invite_code column ──
    if _table_exists('class_group') and not _column_exists('class_group', 'invite_code'):
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE class_group ADD COLUMN invite_code VARCHAR(10)'))
            conn.commit()
            # 为已有班级生成默认邀请码
            from backend.database.models_v2 import PrescriptionPlan  # ensure models loaded
            import secrets, string as _string
            from backend.database.models import ClassGroup
            rows = conn.execute(text('SELECT id FROM class_group WHERE invite_code IS NULL')).fetchall()
            for row in rows:
                code = ''.join(secrets.choice(_string.ascii_uppercase + _string.digits) for _ in range(8))
                conn.execute(text('UPDATE class_group SET invite_code = :code WHERE id = :id'), {'code': code, 'id': row[0]})
            conn.commit()
        # Try to create unique index (may fail on SQLite if duplicates, but we just filled them)
        try:
            with engine.connect() as conn:
                conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS idx_class_group_invite_code ON class_group (invite_code)'))
                conn.commit()
        except Exception:
            pass  # Index may already exist or DB doesn't support

    # ── plan_change_request table ──
    if not _table_exists('plan_change_request'):
        with engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE plan_change_request (
                    id INTEGER NOT NULL AUTO_INCREMENT,
                    plan_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    coach_id INTEGER,
                    status VARCHAR(20) DEFAULT 'pending',
                    original_snapshot TEXT,
                    proposed_items TEXT,
                    coach_items TEXT,
                    coach_notes TEXT,
                    student_notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    FOREIGN KEY (plan_id) REFERENCES prescription_plan(id),
                    FOREIGN KEY (student_id) REFERENCES user(id),
                    FOREIGN KEY (coach_id) REFERENCES user(id)
                )
            '''))
            conn.commit()

    # ── message table ──
    if not _table_exists('message'):
        with engine.connect() as conn:
            conn.execute(text('''
                CREATE TABLE message (
                    id INTEGER NOT NULL AUTO_INCREMENT,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    related_type VARCHAR(20),
                    related_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    FOREIGN KEY (sender_id) REFERENCES user(id),
                    FOREIGN KEY (receiver_id) REFERENCES user(id)
                )
            '''))
            conn.commit()


def init_db():
    # 确保所有模型被导入，SQLAlchemy 才能发现并创建表
    from backend.database import models  # noqa: F401
    from backend.database import models_v2  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # 添加后续新增的列（create_all 只建表不修改已有表）
    run_migrations()
