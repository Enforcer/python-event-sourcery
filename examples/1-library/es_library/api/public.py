from uuid import UUID

from es_library.api.dependencies import copies_repo, db_session
from es_library.api.read_models import BookReadModel
from es_library.borrowing.copy import Copy
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from event_sourcery import Repository

router = APIRouter(prefix="/api/v1")


@router.get("/books")
def list_books(session: Session = Depends(db_session)):
    books = session.query(BookReadModel).filter(BookReadModel.copies_total > 0).all()
    return [
        {
            column.name: getattr(book, column.name)
            for column in BookReadModel.__table__.columns
        }
        for book in books
    ]


@router.post("/books/copies/{copy_uuid}/borrowing")
def borrow_book(
    copy_uuid: UUID,
    session: Session = Depends(db_session),
    repository: Repository[Copy] = Depends(copies_repo),
):
    copy = repository.load(stream_id=copy_uuid)
    copy.borrow()
    repository.save(aggregate=copy, stream_id=copy_uuid)
    session.commit()


@router.delete("/books/copies/{copy_uuid}/borrowing")
def return_book():
    pass
