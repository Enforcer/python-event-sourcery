from datetime import date, datetime
from uuid import UUID

import factory

from event_sourcery import Event


class SomeEvent(Event):
    first_name: str


class SomeEventFactory(factory.Factory):
    class Meta:
        model = SomeEvent

    first_name = factory.Faker("first_name")


class AnotherEvent(Event):
    last_name: str


class NastyEventWithJsonUnfriendlyTypes(Event):
    uuid: UUID
    a_datetime: datetime
    second_datetime: datetime
    a_date: date
