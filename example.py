import os
import uuid

import breakout
import tornado.ioloop
import tornado.web
import tornado.websocket


class TornadoScheduler(breakout.Scheduler):
    def schedule(self, function, delay):
        return tornado.ioloop.IOLoop.current().call_later(
            delay / 1000,
            function
        )

    def cancel(self, task):
        return tornado.ioloop.IOLoop.current().remove_timeout(task)


class Status:
    def __init__(self):
        self._state = breakout.State.CLOSED

    def set_state(self, state):
        self._state = state

    def to_json(self):
        return {'state': self._state.name}


sockets = {}
scheduler = TornadoScheduler()
status = Status()


def write_status(socket):
    socket.write_message(status.to_json())


def subscriber(event):
    if isinstance(event, breakout.CloseEvent):
        status.set_state(breakout.State.CLOSED)
    elif isinstance(event, breakout.ClosingEvent):
        status.set_state(breakout.State.CLOSING)
    else:
        status.set_state(breakout.State.OPEN)

    for socket in sockets.values():
        write_status(socket)


class ExampleHandler(tornado.web.RequestHandler):
    @breakout.circuit_breaker(scheduler=scheduler, subscriber=subscriber)
    async def get(self):
        raise breakout.ServiceUnavailableError()

    def _handle_request_exception(self, error):
        if not isinstance(error, breakout.ServiceUnavailableError):
            raise error

        self.set_status(503)
        self.finish('Oooups! The service is currently unavailable.')


class StatusHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        id = str(uuid.uuid4())
        self.id = id
        sockets[id] = self

        write_status(self)

    def on_close(self):
        sockets.pop(self.id)


def main():
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
