from uuid import uuid4

from es_library.api.dependencies import book_projection, copies_repo, db_session
from es_library.api.projection import BookProjection
from es_library.borrowing.copy import Copy
from es_library.catalog.book import Book
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from event_sourcery import Repository

router = APIRouter(prefix="/private")


@router.get("/books")
def list_books():
    return []


class AddBookPayload(BaseModel):
    title: str
    isbn: str


@router.post("/books")
def add_book(
    payload: AddBookPayload,
    session: Session = Depends(db_session),
    projection: BookProjection = Depends(book_projection),
):
    book = Book(title=payload.title, isbn=payload.isbn)
    session.add(book)
    session.flush()
    projection.initialize(book)  # TODO: via events?
    session.commit()
    return Response(status_code=204)


@router.post("/books/{isbn}/copies")
def register_book_copy(
    isbn: str,
    session: Session = Depends(db_session),
    repository: Repository[Copy] = Depends(copies_repo),
):
    try:
        book = session.query(Book).filter(Book.isbn == isbn).one()
    except NoResultFound:
        return Response(status_code=404)

    stream_id = uuid4()
    copy = Copy(book_id=book.id, copy_uuid=stream_id)
    repository.save(aggregate=copy, stream_id=stream_id)

    session.commit()
    return Response(status_code=204)
