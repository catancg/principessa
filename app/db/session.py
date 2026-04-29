from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL

# SQLAlchemy maps "postgresql://" to psycopg2; force psycopg3 driver.
_db_url = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    _db_url,
    pool_pre_ping=True,
)

# PgBouncer (Supabase pooler) doesn't support named prepared statements.
# Disabling prepare_threshold makes psycopg3 send all queries as simple protocol.
@event.listens_for(engine, "connect")
def disable_prepared_statements(dbapi_connection, _):
    dbapi_connection.prepare_threshold = None

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
