
from typing import *
import asyncio
import json
from functools import partial

import inkBoard

from tornado.websocket import WebSocketHandler

from PythonScreenStackManager import tools
from PythonScreenStackManager.elements import Element, TabPages
from PythonScreenStackManager.exceptions import ShorthandGroupNotFound, ShorthandNotFound

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
        
        try:
            if message["type"] in self.watcher_types:
                self.add_watcher(message)
            elif message["type"] in self.getter_types:
                func = getattr(self,message.pop("type"))
                func(**message)
            elif message["type"] in self.caller_types:
                await self.call_caller(message)
            else:
                self.write_result_message(message["message_id"], f"Unknown type {message['type']}", False)
        except Exception as exce:
            self.write_result_message(message["message_id"], exce, False)

    def close(self, code = None, reason = None):
        self.write_message({"type": "closing", "code": code, "reason": reason})
        return super().close(code, reason)

    def on_close(self):
        _LOGGER.debug("Closed a websocket connection")
        for watcher in self._watchers:
            watcher.cancel("Websocket closed")

        self.application._websockets.remove(self)
        self._connected = False

    def write_message(self, message, binary = False):
        return super().write_message(message, binary)

    def write_id_message(self, message_id : int, type_ : str, message : dict):
        message = {"id": message_id, "type": type_} | message
        return self.write_message(message)

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
        if isinstance(result, Exception):
            result = str(result)
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

    def get_elements(self, message_id : int):
        self.write_result_message(message_id, self.application.get_elements())

    def get_actions(self, message_id: int):
        self.write_result_message(message_id, self.application.get_actions_config())

    def get_element_state(self, message_id : int, element_id : str, properties : list[str]):
        """Gets the state (value) of the provided element properties

        Be mindful that only properties that can be represented via JSON can be returned. If a property is in the list whose value cannot be converted, the server will return an unsuccessfull response.
        Properties whose value are an element can be included, the API takes care of converting the values 
        """        

        element = self.screen.elementRegister.get(element_id, False)
        if element_id == False:
            self.write_result_message(message_id, f"Unknown element_id {element_id}", False)
            return
        
        try:
            element_state = self._gather_element_properties(element, properties)
            self.write_result_message(message_id, {"element_id": element_id, "state": element_state})
        except Exception as exce:
            self.write_result_message(message_id, exce, False)

    def get_feature_state(self, message_id : int, feature : str):
        """Gets the state of a specific device feature
        """        
        try:
            feature_str = FEATURES.get_feature_string(feature)
            if not self.device.has_feature(feature_str):
                self.write_result_message(message_id, f"Device does not have feature {feature}", False)
            else:
                if feature_str == FEATURES.FEATURE_NETWORK:
                    state = self.application.get_network_config()
                else:
                    state = self.device.get_feature_state(feature)
                self.write_result_message(message_id, {"feature": feature_str, "state": state})
        except AttributeError:
            self.write_result_message(message_id, f"{feature} is not a known value for a feature", False)        

    def get_screen_state(self, message_id : int, properties : str):
        """Gets the values of the requested screen attributes.

        The client is responsible for ensuring the values can be serialised to json.
        """        

        try:
            prop_vals = {}
            for prop in properties:
                prop_vals[prop] = getattr(self.screen,prop)

            self.write_result_message(message_id, {"screen_state": prop_vals})
        except Exception as exce:
            self.write_result_message(message_id, exce, False)
        return

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
                feature_state = await condition.wait_for(partial(test_state, feature_state))
            
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
        missing_props = set()
        for prop in property_list:
            if not hasattr(element, prop):
                missing_props.add(prop)
            val = getattr(element, prop)
            
            if isinstance(val,set):
                val = list(val)
            elif isinstance(val,Element):
                val = str(val)

            props[prop] = val
        
        if missing_props:
            raise AttributeError(f"Element does not have {'properties' if len(missing_props) > 1 else 'property'} {missing_props}")
        return props

    async def call_caller(self, message):
        call_func = getattr(self,message.pop("type"))
        await call_func(**message)

    async def call_action(self, message_id : int, action : Union[dict,str]):
        """Call an action

        The syntax is the same as the one used in YAML, just converted to json/dicts

        .. code-block:: json

            {
            "message_id": 1,
            "type" "call_action",
            "action": {
                        "action":"element:set",
                        "element_id": "my-counter",
                        "data": {"value": 5}
                        }
            }
        """        

        if isinstance(action, dict):
            action_dict = action
            data = action_dict.get("data", {})
        else:
            action_dict = {}
            data = {}

        if ":" in action:
            group, action = action.split(":")
            try:
                func = self.application.parse_group_action(group, action, action_dict)
            except ShorthandGroupNotFound:
                self.write_result_message(message_id, f"No shorthand action group {group} is registered", False)
                return
            except ShorthandNotFound:
                self.write_result_message(message_id, f"Shorthand action group {group} could not parse {action}", False)
                return
        else:
            try:
                func = self.application.parse_shorthand_action(action)
            except ShorthandNotFound:
                self.write_result_message(message_id, f"No Shorthand Action {action}", False)
                return

        try:
            tools.validate_action_call(func, keyword_arguments=data)
        except TypeError as exce:
            self.write_result_message(message_id, exce, False)
            return
        
        coro = tools.wrap_to_coroutine(func, **data)
        (res, exce) = await self.application.run_coroutine(coro)
        if res:
            self.write_result_message(message_id, None)
        else:
            self.write_result_message(message_id, f"Could not call action", False)
        return

    watcher_types = ("watch_element", "watch_popups", "watch_device_feature", "watch_interaction")
    getter_types = ("get_config", "get_device_config", "get_elements", "get_actions",
                    "get_element_state", "get_feature_state", "get_screen_state")
    caller_types = ("call_action")


def add_websocket_handler(app: "APICoordinator"):

    app.add_handlers(r'(localhost|127\.0\.0\.1)',
                    [(r"/api/websocket", inkBoardWebSocket)]
    )
    return


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