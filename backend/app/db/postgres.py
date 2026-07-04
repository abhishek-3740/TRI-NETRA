"""
Postgres connection — the absolute source of truth for all case data.
Every write happens here FIRST, inside a transaction, before any Neo4j
projection update is queued (see neo4j_client.py::queue_neo4j_projection_update).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.postgres_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
