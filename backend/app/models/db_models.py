"""
SQLAlchemy models for Postgres — the absolute source of truth.
Neo4j is populated FROM this data, never the other way around.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime)

    entities = relationship("Entity", back_populates="case")


class Entity(Base):
    __tablename__ = "entities"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("cases.id"))
    entity_type = Column(String)   # "account" | "phone" | "upi" | "ip"
    identifier = Column(String)    # the actual account number / phone / VPA / IP
    risk_score = Column(Float, default=0.0)
    is_mule_flagged = Column(Boolean, default=False)

    case = relationship("Case", back_populates="entities")


class Event(Base):
    __tablename__ = "events"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("cases.id"))
    event_type = Column(String)    # "call" | "ip_session" | "transfer" | "bank_login"
    timestamp = Column(Integer)    # IST epoch seconds
    source_entity_id = Column(String, ForeignKey("entities.id"))
    target_entity_id = Column(String, ForeignKey("entities.id"), nullable=True)
    amount = Column(Float, nullable=True)
    metadata_json = Column(String, nullable=True)  # raw extra fields as JSON string


class Transfer(Base):
    __tablename__ = "transfers"
    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("cases.id"))
    from_account_id = Column(String, ForeignKey("entities.id"))
    to_account_id = Column(String, ForeignKey("entities.id"))
    amount = Column(Float)
    timestamp = Column(Integer)

    # NOTE: this table is the exact source used both by the NetworkX fallback
    # AND to rebuild the Neo4j projection via scripts/rebuild_neo4j_from_postgres.sh
