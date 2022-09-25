from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Optional, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, Extra, Field

from event_sourcery.event_registry import EventRegistry
from event_sourcery.interfaces.event import Event as EventProto


class Metadata(BaseModel, extra=Extra.allow):
    correlation_id: Optional[UUID]
    causation_id: Optional[UUID]


class Event(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int | None
    metadata: Metadata = Field(default_factory=Metadata)

    __registry__: ClassVar = EventRegistry()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls.__registry__.add(cls)


if TYPE_CHECKING:
    # for PyCharm to kindly consider pydantic-based Event compatible with EventProto
    Event = cast(EventProto, Event)  # type: ignore
