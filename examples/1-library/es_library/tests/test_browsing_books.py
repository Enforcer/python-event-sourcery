from uuid import UUID

from es_library.tests.dsl import PrivateApi, PublicApi


class AnyInt(int):
    def __eq__(self, other: int) -> bool:
        return isinstance(other, int)

    def __repr__(self) -> str:
        return "<AnyInt>"


class AnyUUIDLikeString:
    def __eq__(self, other: str) -> bool:
        try:
            UUID(other)
        except TypeError:
            return False
        else:
            return True


def test_book_without_copies_is_not_available(
    private_api: PrivateApi, public_api: PublicApi
) -> None:
    private_api.add_book(title="Random", isbn="123")

    assert public_api.list() == []


def test_book_with_one_copy_is_publicly_available(
    private_api: PrivateApi, public_api: PublicApi
) -> None:
    private_api.add_book(title="Another", isbn="321")
    private_api.add_copy(isbn="321")

    assert public_api.list() == [
        {
            "id": AnyInt(),
            "isbn": "321",
            "title": "Another",
            "available": True,
            "copies_total": 1,
            "copies_available": [AnyUUIDLikeString()],
        }
    ]


def test_borrowed_book_is_not_available(
    private_api: PrivateApi, public_api: PublicApi
) -> None:
    private_api.add_book(title="Another", isbn="322")
    private_api.add_copy(isbn="322")

    copy_uuid = public_api.list()[-1]["copies_available"][0]
    public_api.borrow(copy_uuid=copy_uuid)

    assert public_api.list() == [
        {
            "id": AnyInt(),
            "isbn": "322",
            "title": "Another",
            "available": False,
            "copies_total": 1,
            "copies_available": [],
        }
    ]
