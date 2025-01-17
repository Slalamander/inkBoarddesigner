
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
            return

        if "type" not in message:
            self.write_message({"type": "error", "message": "messages must have a type key"})
            return

        self.write_message(u"You said: " + message)

    def on_close(self):
        _LOGGER.debug("Closed a websocket connection")
        self.application._websockets.remove(self)


    messagetypes = {
        # "ping": None, #simply returns the pong -> may not be necessary, idk what tornado does out of the box
        "get_config": None,  #returns the inkBoard config, without the stuff that can change
        "get_device_config": None, ##Returns just the device config?
        "get_actions": None, #Returns the available actions and groups
        "get_state": None,   #return the current state of inkBoard idk
        
        "subscribe_device": None,    #subscribe to device updates -> how to handle passing the changed things?
        "subscribe_elements": None, #subscribe to certain elements doing a thing; this is not implemented though.
        "call_action": None, #calls an action; handles identifier etc. also allow for returning the result
        "t": None
    }

def make_app(app: "APICoordinator"):

    app.add_handlers(r'(localhost|127\.0\.0\.1)',
                    [(r"/api/websocket", inkBoardWebSocket)]
    )
    return