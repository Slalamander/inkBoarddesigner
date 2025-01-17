
from typing import *
import asyncio
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
        self.application._websockets.add(self)
        self._connected = True
        self.write_message({"type": "connection", "inkboard_version": inkBoard.__version__})

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

    def close(self, code = None, reason = None):
        self.write_message({"type": "closing", "reason": reason})
        return super().close(code, reason)

    def on_close(self):
        _LOGGER.debug("Closed a websocket connection")
        self.application._websockets.remove(self)
        self._connected = False


    messagetypes = {
        # "ping": None, #simply returns the pong -> may not be necessary, idk what tornado does out of the box
        "get_config": None,  #returns the inkBoard config, without the stuff that can change
        "get_device_config": None, ##Returns just the device config?
        "get_actions": None, #Returns the available actions and groups
        "get_state": None,   #return the current state of inkBoard idk
        
        "subscribe_device": None,    #subscribe to device updates -> how to handle passing the changed things?
        "subscribe_elements": None, #subscribe to certain elements doing a thing; this is not implemented though.
        "call_action": None, #calls an action; handles identifier etc. also allow for returning the result
    }

    async def _await_device_update(self, message_id, feature):

        ##purely allow subscribing to features.
        while self._connected and self.application.screen.printing:
            
            asyncio.sleep(5)

        ##I think a good way to improve this is to give each feature class a get_state function or something
        ##which should return a dict with anything that is updated on polling. 
        ##These can then be checked into by conditions.

def make_app(app: "APICoordinator"):

    app.add_handlers(r'(localhost|127\.0\.0\.1)',
                    [(r"/api/websocket", inkBoardWebSocket)]
    )
    return