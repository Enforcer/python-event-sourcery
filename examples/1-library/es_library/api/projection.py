from es_library.api.read_models import BookReadModel
from es_library.borrowing.copy import CopyBorrowed, CopyRegistered
from es_library.catalog.book import Book
from sqlalchemy.orm import Session

from event_sourcery.interfaces.event import Event


class BookProjection:
    def __init__(self, session: Session) -> None:
        self._session = session

    def initialize(self, book: Book) -> None:
        # TODO via events? Need to have named streams... They'd come in handy
        self._session.add(
            BookReadModel(
                id=book.id,
                isbn=book.isbn,
                title=book.title,
                available=False,
                copies_total=0,
                copies_available=[],
            )
        )

    def __call__(self, event: Event) -> None:
        match event:
            case CopyRegistered():
                assert event
                read_model = self._session.query(BookReadModel).get(event.book_id)
                read_model.copies_total += 1
                read_model.copies_available = [
                    str(event.copy_uuid)
                ] + read_model.copies_available
                read_model.available = True
            case CopyBorrowed():
                read_model = self._session.query(BookReadModel).get(event.book_id)
                read_model.copies_available = [
                    uuid
                    for uuid in read_model.copies_available
                    if uuid != str(event.copy_uuid)
                ]
                if read_model.copies_available == []:
                    read_model.available = False
