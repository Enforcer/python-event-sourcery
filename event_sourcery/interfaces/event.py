from datetime import datetime
from typing import Any, Optional, Protocol
from uuid import UUID


class Metadata(Protocol):
    correlation_id: Optional[UUID]
    causation_id: Optional[UUID]


class Event(Protocol):
    uuid: UUID
    created_at: datetime
    version: int | None

    def __init__(self, **kwargs: Any) -> None:
        ...  # pragma: no cover

    @property
    def metadata(self) -> Metadata:
        # https://mypy.readthedocs.io/en/latest/common_issues.html#covariant-subtyping-of-mutable-protocol-members-is-rejected
        ...  # pragma: no cover
