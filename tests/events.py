from datetime import date, datetime
from uuid import UUID

import factory

from event_sourcery_pydantic.event import Event as BaseEvent


class SomeEvent(BaseEvent):
    first_name: str


class SomeEventFactory(factory.Factory):
    class Meta:
        model = SomeEvent

    first_name = factory.Faker("first_name")


class AnotherEvent(BaseEvent):
    last_name: str


class NastyEventWithJsonUnfriendlyTypes(BaseEvent):
    uuid: UUID
    a_datetime: datetime
    second_datetime: datetime
    a_date: date
