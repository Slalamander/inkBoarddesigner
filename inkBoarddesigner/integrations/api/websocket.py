
from typing import *
import json

import inkBoard

from tornado.websocket import WebSocketHandler

if TYPE_CHECKING:
    from .app import APICoordinator

_LOGGER = inkBoard.getLogger(__name__)

class inkBoardWebSocket(WebSocketHandler):

    application: "APICoordinator"
    _last_id: int


    async def open(self):
        _LOGGER.debug("Opening a websocket connection")
        self._last_id = 0
        self.write_message({"type": "connection", "inkboard_version": inkBoard.__version__})
        self.application._websockets.add(self)

    async def on_message(self, message):
        
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            self.write_message({"type": "error", "message": "message must be valid json"})
            return
        
        if "id" not in message:
            self.write_message({"type": "error", "message": "a message must contain the id parameter"})
        elif "id" <= self._last_id:
            self.write_message({"type": "error", "message": "message id must be larger than the previous message"})

        self.write_message(u"You said: " + message)

    def on_close(self):
        _LOGGER.debug("Closed a websocket connection")
        self.application._websockets.remove(self)


def make_app(app: "APICoordinator"):

    app.add_handlers(r'(localhost|127\.0\.0\.1)',
                    [(r"/api/websocket", inkBoardWebSocket)]
    )
    return