class EventStoreException(Exception):
    pass


class NoEventsToAppend(EventStoreException):
    pass


class ConcurrentStreamWriteError(EventStoreException):
    pass


class Misconfiguration(EventStoreException):
    pass


class AnotherStreamWithThisNameButOtherIdExists(EventStoreException):
    pass


class EitherStreamIdOrStreamNameIsRequired(EventStoreException):
    pass


class CannotUseExpectedVersionForStreamCreatedWithAnyVersioning(EventStoreException):
    pass


class CannotUseAutoVersioningForStreamCreatedWithAnyVersioning(EventStoreException):
    pass


class CannotUseAnyVersioningForStreamCreatedWithOtherVersioning(EventStoreException):
    pass
