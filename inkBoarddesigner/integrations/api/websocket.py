
from typing import *
import asyncio
import json
from functools import partial

import inkBoard

from tornado.websocket import WebSocketHandler

from PythonScreenStackManager.elements import Element, TabPages

from inkBoard.constants import DEFAULT_MAIN_TABS_NAME
from inkBoard.platforms.basedevice import FEATURES

if TYPE_CHECKING:
    from .app import APICoordinator

_LOGGER = inkBoard.getLogger(__name__)

class inkBoardWebSocket(WebSocketHandler):

    application: "APICoordinator"
    _last_id: int
    _watchers: set[asyncio.Task]

    @property
    def core(self):
        return self.application.core

    @property
    def screen(self):
        return self.application.core.screen
    
    @property
    def device(self):
        return self.application.core.device

    async def open(self):
        _LOGGER.debug("Opening a websocket connection")
        self._last_id = 0
        self.application._websockets.add(self)
        self._connected = True
        self._watchers = set()
        self.write_message({"type": "connection", "inkboard_version": inkBoard.__version__})

    async def on_message(self, message):
        
        try:
            message : dict = json.loads(message)
        except json.JSONDecodeError:
            self.write_message({"type": "error", "message": "message must be valid json"})
            return
        
        if "id" not in message:
            self.write_message({"type": "error", "message": "a message must contain the id parameter"})
        elif message["id"] <= self._last_id:
            self.write_message({"type": "error", "message": "message id must be larger than the previous message"})
            return
        self._last_id = message["id"]
        message["message_id"] = message.pop("id")

        if "type" not in message:
            self.write_message({"type": "error", "message": "messages must have a type key"})
            return
        elif message["type"] in self.watcher_types:
            self.add_watcher(message)
        else:
            self.write_message(u"You said: " + str(message))

    def close(self, code = None, reason = None):
        self.write_message({"type": "closing", "code": code, "reason": reason})
        return super().close(code, reason)

    def on_close(self):
        _LOGGER.debug("Closed a websocket connection")
        for watcher in self._watchers:
            watcher.cancel("Websocket closed")

        self.application._websockets.remove(self)
        self._connected = False

    def write_id_message(self, message_id : int, type_ : str, message : dict):
        message["id"] = message_id
        message["type"] = type_
        return super().write_message(message)

    def write_result_message(self, message_id : int, result, success : bool = True):
        """Writes a message with type 'result'

        If success is false, instead of a 'result' key, the 'message' key is used, and the ``result`` parameter should be the failure reason.

        Parameters
        ----------
        message_id : int
            id of the message this is in response of
        result : any
            The result, or error reason
        success : bool
            If the result is succesfull, by default True
        """        
        message = {"success": True,
                    "result": result}
        return self.write_id_message(message_id, "result", message)
        

    def get_config(self, message_id : int):
        conf = dict(self.application.baseConfig)

        if self.core.config.inkBoard.main_element:
            id = self.core.config.inkBoard.main_element
            main_elt = self.core.screen.elementRegister[id]
            if main_elt.__module__.startswith("PythonScreenStackManager.elements"):
                type_ = main_elt.__module__.split(".")[-1]
            elif main_elt.__module__.startswith("inkBoard.integrations"):
                type_ = main_elt.__module__.lstrip("inkBoard.integrations.")
            else:
                type_ = main_elt.__module__

            conf["main_element"] = {
                "id": id,
                "type": type_
            }
        elif "main_tabs" in self.core.config:
            conf["main_element"] = {
                "id": self.core.config["main_tabs"].get("id", DEFAULT_MAIN_TABS_NAME),
                "type": TabPages.__name__
            }
            main_elt = self.core.screen.elementRegister[conf["main_element"]["id"]]
        else:
            conf["main_element"] = None
            main_elt = None

        if isinstance(main_elt, TabPages):
            conf["main_element"]["tabs"] = list(main_elt.pageNames)

        conf["popups"] = {
            "registered_popups": list(self.core.screen.popupRegister.keys())
        }
        ##Get element state as seperate function I think? Or return it when subscribing? No better for seperate to in case watch is not required
        ##Same with feature states
        ##i.e. seperate get_actions for things that can change.
        self.write_result_message(message_id, conf)
        return

    def get_device_config(self, message_id : int):
        """Returns the device config. 

        device size is only included if the device does not have the resize feature.
        Otherwise, get the size by using get_feature_state
        """
        conf = self.application.get_device_config()

        if not self.device.has_feature(FEATURES.FEATURE_RESIZE):
            conf["size"] = self.device.screenSize

        self.write_result_message(message_id, conf)
        

    def add_watcher(self, message: dict) -> asyncio.Task:
        func = getattr(self, message.pop("type"))
        watcher = asyncio.create_task(func(**message))
        self._watchers.add(watcher)
        return watcher

    async def watch_device_feature(self, message_id : int, feature : str):
        """Notifies clients when the requested device feature has updated
        """
        try:
            feature_str = FEATURES.get_feature_string(feature)
        except AttributeError as exce:
            self.write_id_message(message_id, "result", {"success": False,
                                "message": str(exce)})
            return

        if not self.device.has_feature(feature_str):
            self.write_id_message(message_id, "result", {"success": False,
                    "message": f"Device does not have feature {feature_str} (passed as {feature})"})
            return
        
        condition = self.device.get_feature_trigger(feature_str)
        feature_state = self.device.get_feature_state(feature_str)
        if not condition:
            self.write_id_message(message_id, "result", {"success": False,
                "message": f"Feature {feature} cannot be watched"})
            return
        
        def test_state(feature_state):
            current_state = self.device.get_feature_state(feature_str)
            res = current_state != feature_state
            if res:
                return current_state
            else:
                return False

        self.write_id_message(message_id, "result", {"success": True,
            "message": f"Succesfully watching device feature {feature_str} from {feature}"})
        while not self.close_code:
            async with condition:
                ##Can use the result from the predicate, so can try a custom function or something that returns False if no update
                # await condition.wait_for(lambda: feature_state != self.device.get_feature_state(feature_str))
                feature_state = await condition.wait_for(partial(test_state, feature_state))
            
            # feature_state = self.device.get_feature_state(feature_str)
            self.write_id_message(message_id, "watch_device_feature",
                                {"feature": feature_str, "feature_state": feature_state})
        return

    async def watch_popups(self, message_id : int):
        """Notifies clients when the popups on top of the screen change
        """
        condition = self.screen.triggerCondition
        self.write_id_message(message_id, "result", {"success": True})
        while not self.close_code:
            popup_list = self.screen.popupsOnTop.copy()
            popup_strings = [popup.popupID for popup in self.screen.popupsOnTop if hasattr(popup, "popupID")]
            self.write_id_message(message_id, "watch_popups", {"popups": popup_strings})
            async with condition:
                await condition.wait_for(lambda: popup_list != self.screen.popupsOnTop)
        
        _LOGGER.debug("stopped watching popups")

    async def watch_element(self, message_id : int, element_id : str, properties : list[str]):
        """Watches an element and notifies a client when the associated property has updated

        Can be used to, for example, to be notified of a :py:class:`PythonScreenStackManager.elements.TabPages`` changing the page being shown.
        """

        ##Each update: write a dict with the new properties
        try:
            element = self.screen.elementRegister[element_id]
            condition = element.triggerCondition
            elt_dict = self._gather_element_properties(element, properties)
            self.write_id_message(message_id, "result", {"success": True})
        except KeyError:
            self.write_id_message(message_id, "result", {"success": False, "message": f"No element with id {element_id}"})
            return
        except AttributeError as exce:
            self.write_id_message(message_id, "result", {"success": False, "message": str(exce)})
            return
        except Exception:
            self.write_id_message(message_id, "result", {"success": False, "message": str(exce)})
            return
        
        while not self.close_code:
            
            async with condition:
                await condition.wait_for(lambda: elt_dict != self._gather_element_properties(element, properties))

            elt_dict = self._gather_element_properties(element, properties)
            self.write_id_message(message_id, "watch_element",
                        {"element_id": element_id,
                        "properties": elt_dict
                        })
        return

    async def watch_interaction(self, message_id: int):
        """Notifies clients when an interaction event is dispatched
        """

        condition = self.screen.touchTrigger
        self.write_id_message(message_id, "result",
                            {"success": True})
        
        while not self.close_code:
            await condition.await_trigger()
            self.write_id_message(message_id, "watch_interaction",
                            {"touch_event": self.screen.lastTouch._asdict()})

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

    watcher_types = ("watch_element", "watch_popups", "watch_device_feature", "watch_interaction")

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