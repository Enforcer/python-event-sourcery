from typing import Iterator

from es_library import db
from es_library.api.projection import BookProjection
from es_library.borrowing.copy import Copy
from fastapi import Depends
from sqlalchemy.orm import Session

from event_sourcery import EventStore, Repository, get_event_store
from event_sourcery.interfaces.event import Event


def db_session() -> Iterator[Session]:
    session = Session(bind=db.engine)
    try:
        yield session
    finally:
        session.close()


def book_projection(session: Session = Depends(db_session)) -> EventStore:
    return BookProjection(session)


def event_store(
    session: Session = Depends(db_session),
    books_projection: BookProjection = Depends(book_projection),
) -> EventStore:
    return get_event_store(session, subscriptions={Event: [books_projection]})


def copies_repo(event_store: EventStore = Depends(event_store)) -> Repository[Copy]:
    return Repository[Copy](event_store, Copy)
