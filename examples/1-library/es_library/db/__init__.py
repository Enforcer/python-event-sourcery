from sqlalchemy import create_engine
from sqlalchemy.orm import as_declarative

from event_sourcery import configure_models

engine = create_engine(
    "postgresql://event_sourcery:event_sourcery@localhost:5432/event_sourcery"
)


@as_declarative()
class Base:
    pass


configure_models(Base)
