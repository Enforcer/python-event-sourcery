from datetime import timedelta
from queue import Queue, Empty
from time import sleep, monotonic
from threading import Thread
from typing import Iterator, Protocol, Iterable


def backend(start_from: int) -> Iterator[int]:
    """
    BELONGS TO BACKEND IMPLEMENTATION,
    to simulate that events sometimes are not available immediately

    Idea:
    StopIteration or other mechanism - backend could signal there's nothing left to iterate.
    """
    for num in range(start_from, 100_000):
        sleep(0.5 if num % 10 != 0 else 6)
        yield num


def lame_take(count: int, within: timedelta, iterable: Iterator[int]) -> Iterator[list[int]]:
    """
    BELONGS TO BACKEND IMPLEMENTATION

    Idea: when gc garbage-collects this Generator of batches,
    then Thread/whatever underlying mechanism (subscription in EventStoreDB)
    then it should be closed/killed etc.
    """
    q = Queue()
    t = Thread(target=lambda: consume_in_thread(q, iterable), daemon=True)
    t.start()

    while True:
        now = monotonic()
        timeout = within.total_seconds()
        timeout_at = now + timeout
        batch = []

        while ((left := timeout_at - monotonic()) >= 1) and len(batch) < count:
            try:
                batch.append(q.get(block=True, timeout=int(left)))
            except Empty:
                break

        yield batch


def consume_in_thread(q: Queue, iterable: Iterator[int]) -> None:
    print("Consuming")
    for item in iterable:
        q.put(item)


class Builder(Protocol):
    def build_iter(self, count: int, within: timedelta) -> Iterator[int]:
        pass

    def build_batch(self, count: int, within: timedelta) -> Iterator[list[int]]:
        pass


class FaustLikeIterablish(Iterable[int]):
    def take(self, count: int, within: timedelta) -> Iterator[list[int]]:
        pass


class EventStore:
    def subscribe(self, start_from: int) -> Builder | FaustLikeIterablish:
        start_backend_subscription = lambda: backend(start_from=start_from)

        # Summary:
        #    We have 2 different solutions implemented:
        #       Builder with `build_iter`, `build_batch`
        #       FaustLikeIterablish with `__iter__` and `take`
        # Conclusion #1: use passing instead of closures
        # Conclusion #2: it is beneficial to have parameters to control latency
        #   in iteration one by one. However, naming could be less confusing
        #   by making it more latency-oriented
        # Conclusion #3: Hence, lack of possibility to pass arguments to
        #       __iter__ in 2nd approach is worrying
        # Conclusion #4: Both approaches (Builder and FaustLikeIterablish are stateless)
        #       whereas returned objects are stateful. However, for __iter__ and take from
        #       FaustLikeIterablish passing it to `for` means starting over.
        #       one would have to pass result of __iter__  to `iter()` which
        #       would be confusing and increases cognitive load
        #

        class IterableOneByOne(Iterator[int]):
            def __init__(self, count: int, within: timedelta) -> None:
                self._count = count
                self._within = within
                self._iterator = None

            def __next__(self) -> int:
                self._start_iteration_if_not_started()
                return next(self._iterator)

            def _start_iteration_if_not_started(self):
                if self._iterator is None:
                    self._iterator = self._start_iteration()

            def __iter__(self) -> Iterator[int]:
                return self

            def _start_iteration(self) -> Iterator[int]:
                iterable = start_backend_subscription()
                generator = lame_take(count=self._count, within=self._within, iterable=iterable)
                for batch in generator:
                    for item in batch:
                        yield item

        class BuilderoIterable(Builder, FaustLikeIterablish):
            # Version with build_``
            def build_iter(self, count: int, within: timedelta) -> Iterator[int]:
                """Rethink naming of parameters to make sense in terms of latency."""
                return IterableOneByOne(count=count, within=within)

            def build_batch(self, count: int, within: timedelta) -> Iterator[list[int]]:
                iterable = start_backend_subscription()
                generator = lame_take(count=count, within=within, iterable=iterable)
                for batch in generator:
                    yield batch

            # Version Faust-like
            def __iter__(self) -> Iterator[int]:
                # HMM, what about args here? Pass it via subscribe_*?
                return IterableOneByOne(count=3, within=timedelta(seconds=5))

            def take(self, count: int, within: timedelta) -> Iterator[list[int]]:
                iterable = start_backend_subscription()
                generator = lame_take(count=count, within=within, iterable=iterable)
                for batch in generator:
                    yield batch

        return BuilderoIterable()


event_store = EventStore()
iterator_one_by_one = event_store.subscribe(start_from=50).build_iter(count=3, within=timedelta(seconds=5))
for item in iterator_one_by_one:
    print(f"Got {item} in 1st iteration")
    if item > 60:
        break

for item in iterator_one_by_one:
    print(f"Got {item} in 2nd iteration")
    break


iterator_by_batch = event_store.subscribe(start_from=12).build_batch(count=3, within=timedelta(seconds=5))
for i, batch in enumerate(iterator_by_batch):
    print(f"Got batch {batch}")
    if i > 3:
        break

iterator_by_batch = event_store.subscribe(start_from=15).build_batch(count=3, within=timedelta(seconds=5))
for batch in iterator_by_batch:
    print(f"Got batch {batch}")
    break


# THE DIFFERENCE IS THAT even if we assign result of `event_store.subscribe(start_from=11)`
# resuming (multiple for's) would cause restarting
# unless we rework it into iterator but this causes confusion with present iter and take methods
subscription = event_store.subscribe(start_from=11)
for item in subscription:
    pass

# WOULD START OVER
# for item in subscription:
#     pass
# WOULD KEEP STATE IF USED `iter`
# subscription = iter(event_store.subscribe(start_from=11))
# for item in subscription:
#   pass

# Take would also be made from the beginning (start_from passed to .subscribe)
for batch in subscription.take(count=3, within=timedelta(seconds=5)):
    pass
