from datetime import datetime
from typing import TypedDict
from uuid import UUID


class RawEventDict(TypedDict):
    uuid: UUID
    stream_id: UUID
    created_at: datetime
    version: int | None
    name: str
    data: dict
    metadata: dict
