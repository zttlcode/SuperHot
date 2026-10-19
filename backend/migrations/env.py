from alembic import context
from app.db import Base, engine
from app import models  # noqa: F401

with engine.connect() as connection:
    sqlite = engine.dialect.name == 'sqlite'
    # Batch migrations rebuild parent tables. With FK enforcement enabled,
    # SQLite would cascade-delete child posts/runs while dropping the old table.
    # This dedicated migration connection is used before API/worker startup.
    if sqlite:
        connection.exec_driver_sql('PRAGMA foreign_keys=OFF')
        connection.commit()
    try:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True, render_as_batch=sqlite)
        with context.begin_transaction():
            context.run_migrations()
        if sqlite and connection.exec_driver_sql('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('Database migration left invalid foreign keys')
    except Exception:
        connection.rollback()
        raise
    finally:
        if sqlite:
            connection.commit()
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
