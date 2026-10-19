from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False, 'timeout': 30} if DATABASE_URL.startswith('sqlite:') else {}, pool_pre_ping=True)
if DATABASE_URL.startswith('sqlite:'):
    @event.listens_for(engine, 'connect')
    def sqlite_settings(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')


class Base(DeclarativeBase):
    pass


Session = sessionmaker(engine, expire_on_commit=False)


def session():
    with Session() as db:
        yield db
