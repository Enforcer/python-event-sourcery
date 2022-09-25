from typing import Type

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String
from sqlalchemy.ext.declarative import instrument_declarative

from event_sourcery_sqlalchemy.guid import GUID
from event_sourcery_sqlalchemy.jsonb import JSONB


def configure_models(base: Type) -> None:
    for model_cls in (Stream, Event, Snapshot, OutboxEntry):
        instrument_declarative(model_cls, {}, base.metadata)


class Stream:
    __tablename__ = "event_sourcery_streams"

    uuid = Column(GUID(), primary_key=True)
    name = Column(String(40), unique=True, nullable=True)
    version = Column(BigInteger(), nullable=True)


class Event:
    __tablename__ = "event_sourcery_events"
    __table_args__ = (
        Index(
            "ix_events_stream_id_version",
            "stream_id",
            "version",
            unique=True,
        ),
    )

    id = Column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    version = Column(Integer(), nullable=True)
    uuid = Column(GUID(), index=True, unique=True)
    stream_id = Column(GUID(), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    data = Column(JSONB(), nullable=False)
    event_metadata = Column(JSONB(), nullable=False)
    created_at = Column(DateTime(), nullable=False, index=True)


class Snapshot:
    __tablename__ = "event_sourcery_snapshots"

    uuid = Column(GUID, primary_key=True)
    version = Column(Integer(), nullable=False)
    stream_id = Column(GUID(), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    data = Column(JSONB(), nullable=False)
    event_metadata = Column(JSONB(), nullable=False)
    created_at = Column(DateTime(), nullable=False)


class OutboxEntry:
    __tablename__ = "event_sourcery_outbox_entries"

    id = Column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    created_at = Column(DateTime(), nullable=False, index=True)
    data = Column(JSONB(), nullable=False)
    tries_left = Column(Integer(), nullable=False, server_default="3")
