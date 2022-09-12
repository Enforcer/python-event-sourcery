from dataclasses import dataclass

from fastapi.testclient import TestClient


@dataclass
class PublicApi:
    _client: TestClient

    def list(self):
        return self._client.get("/api/v1/books").json()

    def borrow(self, copy_uuid: str):
        return self._client.post(f"/api/v1/books/copies/{copy_uuid}/borrowing").json()

    def return_(self, copy_uuid: str):
        return self._client.delete(f"/api/v1/books/copies/{copy_uuid}/borrowing").json()


@dataclass
class PrivateApi:
    _client: TestClient

    def list(self):
        pass

    def add_book(self, title: str, isbn: str) -> None:
        response = self._client.post(
            "/private/books", json={"title": title, "isbn": isbn}
        )
        assert response.status_code == 204

    def add_copy(self, isbn: str) -> None:
        response = self._client.post(f"/private/books/{isbn}/copies")
        assert response.status_code == 204
