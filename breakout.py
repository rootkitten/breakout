"""
Breakout is a tiny implementation of the circuit breaker microservice pattern for
asynchronous frameworks.
"""

from enum import IntEnum


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
    """
    A base type for all events emitted by a circuit breaker.
    """


class CloseEvent(Event):
    """
    An event type that gets emitted by a circuit breaker whenever its associated
    circuit gets closed.
    """


class ClosingEvent(Event):
    """
    An event type that gets emitted by a circuit breaker whenever its associated
    circuit enters the closing state.
    """


class OpenEvent(Event):
    """
    An event type that gets emitted by a circuit breaker whenever its associated
    circuit gets open.
    """


class Scheduler:
    """
    An interface used internally by a circuit breaker to schedule transitions among its
    individual states.

    The breakout module does not provide a concrete implementation of this interface to
    stay as flexible as possible, but it should be a trivial coding excercise to write a
    proper implementation of this interface using your favorite asynchronous framework.
    In case you find yourself in trouble, I recommend skimming through the sources of
    the provided example app.
    """

    def schedule(self, function, delay):
        """
        An interface method that schedules a delayed call of a passed function.
        """

        raise NotImplementedError('Scheduler interface has to be implemented!')

    def cancel(self, task):
        """
        An interface method that cancels a previously scheduled function call.
        """

        raise NotImplementedError('Scheduler interface has to be implemented!')


class ServiceUnavailableError(Exception):
    """
    An error signaling that a remote service is unavailable. This class is meant to be
    subclassed and raised by any function that wishes to notify a circuit breaker about
    an unacessible remote service.
    """


class State(IntEnum):
    """
    An enumeration of states that is used internally by a circuit breaker.
    """

    CLOSED = 0
    CLOSING = 1
    OPEN = 2


class CircuitBreaker:
    """
    The core circuit breaker state handler. This is where all of the magic happens.
    """

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
        """
        A private method used to publish a circuit breaker events to a subscriber, if
        it exists.
        """

        subscriber = self._subscriber

        if subscriber is not None:
            subscriber(event)

    def _open(self):
        """
        A private method responsible for opening a circuit breaker.
        """

        self._state = State.OPEN
        self._task = self._scheduler.schedule(
            self._half_close,
            self._open_interval
        )

        self._publish(OpenEvent())

    def _half_close(self):
        """
        A private method responsible for half closing a circuit breaker.
        """

        self._state = State.CLOSING
        self._task = self._scheduler.schedule(
            self._close,
            self._closing_interval
        )

        self._publish(ClosingEvent())

    def _close(self):
        """
        A private method responsible for closing a circuit breaker.
        """

        self._errors = 0
        self._state = State.CLOSED

        self._publish(CloseEvent())

    def on_error(self):
        """
        A public method used for notifying a circuit breaker about remote call errors.
        """

        if self._state == State.CLOSING:
            self._scheduler.cancel(self._task)
            self._open()

            return

        self._errors += 1

        if self._errors > self._error_limit:
            self._open()

    def on_success(self):
        """
        A public method used for notifying a circuit breaker about successful remote
        calls.
        """

        if self._state != State.CLOSING:
            return

        self._scheduler.cancel(self._task)
        self._close()

    def is_open(self):
        """
        A public method that returns a boolean value, indicating whether a circuit
        breaker is currently open or not.
        """

        return self._state == State.OPEN


def circuit_breaker(
        error_factory=ServiceUnavailableError,
        error_limit=10,
        open_interval=10000,
        closing_interval=5000,
        scheduler=None,
        subscriber=None
):
    """
    A configurable functional interface used to wrap your remote calls with a circuit
    breaker. It can be used either as a decorator or, if you demand more flexibility,
    as a function.

    The default configuration creates a circuit breaker that tolerates 10 errorneous
    calls, enters closing state after 10 seconds, and closes again after next 5
    seconds.

    Note that the `scheduler` parameter is required.
    """

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
