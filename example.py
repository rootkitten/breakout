"""
A minimal example demonstrating the core capabilities of the Breakout module.
"""

import os

from uuid import uuid4

import tornado.ioloop
import tornado.web
import tornado.websocket

import breakout


class TornadoScheduler(breakout.Scheduler):
    """
    An example implementation of Breakout scheduler interface using the Tornado
    framework.
    """

    def schedule(self, function, delay):
        return tornado.ioloop.IOLoop.current().call_later(
            delay / 1000,
            function
        )

    def cancel(self, task):
        return tornado.ioloop.IOLoop.current().remove_timeout(task)


class Status:
    """
    A class that represents a status of the example app.
    """

    def __init__(self):
        self._state = breakout.State.CLOSED

    def set_state(self, state):
        """
        Sets a state that reflects the current state of the only circuit breaker used
        in this example app.
        """

        self._state = state

    def to_json(self):
        """
        Turns the status object into a JSON dictionary.
        """

        return {'state': self._state.name}


sockets = {}
scheduler = TornadoScheduler()
status = Status()

def generate_uuid():
    """
    A utility method that generates a UUIDv4.
    """

    return str(uuid4())


def write_status(socket):
    """
    Writes the current status to the WebSocket client.
    """

    socket.write_message(status.to_json())


def subscriber(event):
    """
    An example circuit breaker subscriber that processes events emitted by the only
    circuit breaker used by this example app.
    """

    if isinstance(event, breakout.CloseEvent):
        status.set_state(breakout.State.CLOSED)
    elif isinstance(event, breakout.ClosingEvent):
        status.set_state(breakout.State.CLOSING)
    else:
        status.set_state(breakout.State.OPEN)

    for socket in sockets.values():
        write_status(socket)


class ExampleHandler(tornado.web.RequestHandler):
    """
    An example endpoint handler using the circui breaker pattern.
    """

    @breakout.circuit_breaker(scheduler=scheduler, subscriber=subscriber)
    async def get(self):
        raise breakout.ServiceUnavailableError()

    def _handle_request_exception(self, error):
        if not isinstance(error, breakout.ServiceUnavailableError):
            raise error

        self.set_status(503)
        self.finish('Oooups! The service is currently unavailable.')


class StatusHandler(tornado.websocket.WebSocketHandler):
    """
    A WebSocket endpoint that publishes the events of the only circuit breaker used
    by this example app.
    """

    def open(self):
        uuid = generate_uuid()
        self.uuid = uuid
        sockets[uuid] = self

        write_status(self)

    def on_close(self):
        sockets.pop(self.uuid)


def main():
    """
    A main method that gets the whole party started.
    """

    port = 8888

    app = tornado.web.Application([
        (r'/example', ExampleHandler),
        (r'/status', StatusHandler),
        (r'/(.*)', tornado.web.StaticFileHandler, {
            'path': os.path.dirname(__file__),
            'default_filename': 'index.html'
        })
    ])

    print(f'Running the Breakout example app on port {port}.')

    app.listen(port)
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
