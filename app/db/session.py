from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
 
from app.core.config import settings
 
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
 
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {"echo": False, "pool_pre_ping": True, "connect_args": connect_args}
 
if not is_sqlite:
    engine_kwargs.update(pool_size=10, max_overflow=20, pool_recycle=1800)
 
engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
 
if is_sqlite:
 
    # Bound to this specific engine instance (not the Engine class globally)
    # so a differently-configured engine created elsewhere in the process
    # (e.g. a Postgres engine in a test) never has an invalid SQLite PRAGMA
    # issued against it.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
 
 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
 
 
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
 
