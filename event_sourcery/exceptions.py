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
