
from typing import *
import asyncio
import json

import inkBoard

from tornado.websocket import WebSocketHandler

from PythonScreenStackManager.elements import Element

from inkBoard.constants import DEFAULT_MAIN_TABS_NAME

if TYPE_CHECKING:
    from .app import APICoordinator

_LOGGER = inkBoard.getLogger(__name__)

class inkBoardWebSocket(WebSocketHandler):

    application: "APICoordinator"
    _last_id: int

    @property
    def screen(self):
        return self.application.core.screen

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
        elif message["id"] <= self._last_id:
            self.write_message({"type": "error", "message": "message id must be larger than the previous message"})
            return
        self._last_id = message["id"]

        if "type" not in message:
            self.write_message({"type": "error", "message": "messages must have a type key"})
            return
        elif message["type"] in self.watcher_types:
            func = getattr(self, message.pop("type"))
            asyncio.create_task(func(**message))
        else:
            self.write_message(u"You said: " + str(message))

    def close(self, code = None, reason = None):
        self.write_message({"type": "closing", "code": code, "reason": reason})
        return super().close(code, reason)

    def on_close(self):
        _LOGGER.debug("Closed a websocket connection")
        self.application._websockets.remove(self)
        self._connected = False

    watcher_types = {
        "watch_element": "watch_element",
        "watch_popups": "watch_popups"
    }

    messagetypes = {
        # "ping": None, #simply returns the pong -> may not be necessary, idk what tornado does out of the box
        "get_config": None,  #returns the inkBoard config, without the stuff that can change
        "get_device_config": None, ##Returns just the device config?
        "get_actions": None, #Returns the available actions and groups
        "get_state": None,   #return the current state of inkBoard idk
        "call_action": None, #calls an action; handles identifier etc. also allow for returning the result

        "watch_device_feature": None,    #subscribe to device updates -> how to handle passing the changed things?
        ##some features may require a special watcher, like rotation/size

        "watch_element": None, #subscribe to certain elements doing a thing; this is not implemented though. -> how to determine what is watched for?
        ##I think: pass a property dict. watcher will check if the properties changed.
        
        "watch_popups": None,  #subscribe for registered popups being shown/removed
    }

    async def watch_device_features(self, id : str):
        
        return

    async def watch_popups(self, id : str):
        
        condition = self.screen.triggerCondition
        while self.screen.printing:
            popup_list = self.screen.popupsOnTop.copy()
            popup_strings = [popup.popupID for popup in self.screen.popupsOnTop if hasattr(popup, "popupID")]
            self.write_message({"id": id, "type": "watch_popups", "popups": popup_strings})
            async with condition:
                # if popup:
                #     print(f"Popup {popup.popupID} is currently on top")
                # else:
                #     print("No popup is currently on top")
                await condition.wait_for(lambda: popup_list != self.screen.popupsOnTop) 

    async def watch_element(self, id : str, element_id : str, properties : list[str]):

        ##Each update: write a dict with the new properties
        message_id = id
        element = self.screen.elementRegister[element_id]
        condition = element.triggerCondition
        elt_dict = self._gather_element_properties(element, properties)
        self.write_message({"id": message_id, "type": "result", "success": True, "message": f"Watching element {element_id}"})
        while not self.close_code:
            
            async with condition:
                await condition.wait_for(lambda: elt_dict != self._gather_element_properties(element, properties))

            elt_dict = self._gather_element_properties(element, properties)
            self.write_message({"id": message_id, 
                        "type": "watch_element",
                        "element_id": element_id,
                        "properties": elt_dict
                        })
        return

    @staticmethod
    def _gather_element_properties(element, property_list: list[str]) -> dict[str,Any]:

        props = {}
        for prop in property_list:
            val = getattr(element, prop)
            
            if isinstance(val,set):
                val = list(val)
            elif isinstance(val,Element):
                val = str(val)

            props[prop] = val
        return props

def make_app(app: "APICoordinator"):

    app.add_handlers(r'(localhost|127\.0\.0\.1)',
                    [(r"/api/websocket", inkBoardWebSocket)]
    )
    return


watchable_features = {
    "battery", "network", "backlight", "rotation", "resize"
}

##Important examples to remember:

##Watch the page of the maintabs:
# {"id": ..., "type":"watch_element",
# "element_id": element_id,
# "properties": ["currentPage"]
# }

##Watch a specific popup being opened and closed:
# {"id": ..., "type":"watch_element",
# "element_id": element_id,
# "properties": ["onScreen"]
# }