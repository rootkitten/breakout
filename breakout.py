__version__ = '0.0.1'
__all__ = [
    'Event',
    'CircuitBreaker',
    'CloseEvent',
    'ClosingEvent',
    'OpenEvent',
    'Scheduler',
    'ServiceUnavailableError',
    'State',
    'circuit_breaker'
]


class Event:
    pass


class CloseEvent(Event):
    pass


class ClosingEvent(Event):
    pass


class OpenEvent(Event):
    pass


class Scheduler:
    def schedule(self, function, delay):
        raise NotImplementedError('Scheduler interface has to be implemented!')

    def cancel(self, task):
        raise NotImplementedError('Scheduler interface has to be implemented!')


class ServiceUnavailableError(Exception):
    pass


class State:
    CLOSED = 0
    CLOSING = 1
    OPEN = 2


class CircuitBreaker:
    def __init__(
        self,
        error_limit,
        open_interval,
        closing_interval,
        scheduler,
        subscriber=None
    ):
        self._error_limit = error_limit
        self._open_interval = open_interval
        self._closing_interval = closing_interval
        self._scheduler = scheduler
        self._subscriber = subscriber

        self._errors = 0
        self._state = State.CLOSED
        self._task = None

    def _publish(self, event):
        subscriber = self._subscriber

        if subscriber is not None:
            subscriber(event)

    def _open():
        self._state = State.OPEN
        self._task = self._scheduler.schedule(
            self._half_close,
            self._open_interval
        )

        self._publish(OpenEvent())

    def _half_close():
        self._state = State.CLOSING
        self._task = self._scheduler.schedule(
            self._close,
            self._closing_interval
        )

        self._publish(ClosingEvent())

    def _close():
        self._errors = 0
        self._state = State.CLOSED

        self._publish(CloseEvent())

    def on_error():
        if self._state == State.CLOSING:
            self._scheduler.cancel(self._task)
            self._open()

            return

        self._errors += 1

        if self._errors > self._error_limit:
            self._open()

    def on_success():
        if self._state != State.CLOSING:
            return

        self._options.scheduler.cancel(self._task)
        self._close()

    def is_open():
        return self._state == State.OPEN


def circuit_breaker(
    error_factory=ServiceUnavailableError,
    error_limit=10,
    open_interval=10000,
    closing_interval=5000,
    scheduler=None,
    subscriber=None
):
    if not isinstance(scheduler, Scheduler):
        raise ValueError('Scheduler instance is required.')

    breaker = CircuitBreaker(
        error_limit,
        open_interval,
        closing_interval,
        scheduler,
        subscriber=subscriber
    )

    def wrapper(function):
        async def wrap(*args, **kwargs):
            if breaker.is_open():
                raise error_factory()

            try:
                value = await function(*args, **kwargs)

                breaker.on_success()

                return value
            except ServiceUnavailableError as error:
                breaker.on_error()

                raise error

        return wrap

    return wrapper
