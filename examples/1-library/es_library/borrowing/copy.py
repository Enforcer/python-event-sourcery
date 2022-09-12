from uuid import UUID

from event_sourcery import Aggregate, Event


class CopyRegistered(Event):
    book_id: int
    copy_uuid: UUID


class CopyBorrowed(Event):
    book_id: int
    copy_uuid: UUID


class CopyReturned(Event):
    pass


class DomainException(Exception):
    pass


class Copy(Aggregate):
    def __init__(self, book_id: int, copy_uuid: UUID) -> None:
        super().__init__()
        self._event(CopyRegistered, book_id=book_id, copy_uuid=copy_uuid)

    def _apply(self, event: Event) -> None:
        match event:
            case CopyRegistered():
                self._uuid = event.copy_uuid
                self._book_id = event.book_id
                self._taken = False
            case CopyReturned():
                self._taken = False
            case CopyBorrowed():
                self._taken = True

    def borrow(self) -> None:
        if self._taken:
            raise DomainException("Can't borrow borrowed copy!")
        self._event(CopyBorrowed, book_id=self._book_id, copy_uuid=self._uuid)
