"Sets up the api server for inkBoard"

from typing import *
import json

from dataclasses import asdict

import asyncio
import tornado
from tornado.web import RequestHandler

import inkBoard
from inkBoard.platforms import InkboardDeviceFeatures, FEATURES
from inkBoard.constants import DEFAULT_MAIN_TABS_NAME

import PythonScreenStackManager
from PythonScreenStackManager import tools
from PythonScreenStackManager.exceptions import ShorthandNotFound, ShorthandGroupNotFound
from PythonScreenStackManager.elements import TabPages

from .constants import DEFAULT_PORT
from .app import APICoordinator

if TYPE_CHECKING:
    from inkBoard import core as CORE
    from inkBoard.platforms import BaseDevice

class inkBoardAPIServer(tornado.web.Application):

    def __init__(self, handlers = None, default_host = None, transforms = None, **settings):
        super().__init__(handlers, default_host, transforms, **settings)

        self._removed_actions = set()
        self._removed_action_groups = set()

    @property
    def core(self) -> "CORE":
        return self._core
    
    @property
    def device(self) -> "BaseDevice":
        return self._core.device
    
    @property
    def server(self) -> tornado.httpserver.HTTPServer:
        return self._server

    def remove_action_access(self, action: str):
        """Prevents an action shorthand from being callable via the api

        This will throw a 404 error if the action is called

        Parameters
        ----------
        action : str
            The action to remove
        """
        self._removed_actions.add(action)

    def remove_action_group_access(self, action_group: str):
        """Prevents an action group from being callable via the api

        This will throw a 404 error if the group is called.

        Parameters
        ----------
        action_group : str
            The action group to remove
        """
        self._removed_action_groups.add(action_group)


class RequestHandler(RequestHandler):

    application: "APICoordinator"

    @property
    def core(self) -> "CORE":
        return self.application.core
    
    json_args : Optional[dict]

    def prepare(self):
        if self.request.headers.get("content-type", "").startswith("application/json"):
            if self.request.body:
                self.json_args = json.loads(self.request.body)
            else:
                self.json_args = {}
        else:
            self.json_args = None

class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        self.write({"message": "API running"})

class ConfigGetter(RequestHandler):

    def get(self):

        conf = self.application.get_rest_config()
        self.write(conf)
        return

        conf = {}
        conf["name"] = self.core.config.inkBoard.name

        conf["start_time"] = self.core.IMPORT_TIME
        conf["platform"] = self.core.device.platform
        conf["version"] = inkBoard.__version__

        conf["integrations"] = tuple(self.core.integration_loader.imported_integrations.keys())
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
            conf["main_element"]["current_tab"] = main_elt.currentPage
            conf["main_element"]["tabs"] = list(main_elt.pageNames)
            ##Gather the page id's from the element.
            ##Also: add current tab in info as well as optional popup that is on top
        
        conf["popups"] = {
            "current_popup": self.core.screen.popupsOnTop[-1] if self.core.screen.popupsOnTop else None,
            "registered_popups": list(self.core.screen.popupRegister.keys())
        }

        self.write(conf)

class DeviceHandler(RequestHandler):
    """Returns a list with the device's features

    Parameters
    ----------
    RequestHandler : _type_
        _description_
    """

    async def get(self):
        # device = self.core.device
        # conf = {
        #     "platform": device.platform,
        #     "model": device.model,
        #     "name": device.name,
        #     "size": (device.screenWidth, device.screenHeight),
        #     "screen_type": device.screenType,
        #     "screen_mode": device.screenMode
        #     }
        
        # if device.has_feature(FEATURES.FEATURE_ROTATION):
        #     conf["rotation"] = device.rotation

        # features = []
        # for feat, val in self.application.device._features._asdict().items():
        #     if val: features.append(feat)
        
        # conf["features"] = features
        
        conf = self.application.get_device_config()
        self.write(conf)

class BaseFeatureHandler(RequestHandler):

    feature = None

    def prepare(self):
        if not self.core.device.has_feature(self.feature):
            self.send_error(404, reason = "device does not have the battery feature")
            return
        return super().prepare()

class BatteryHandler(BaseFeatureHandler):

    feature = FEATURES.FEATURE_BATTERY

    def get(self):
        # conf = {
        #     "state": self.core.device.battery.state,
        #     "charge": self.core.device.battery.charge
        # }
        conf = self.application.get_battery_config()
        self.write(conf)

    async def post(self):
        """Updates the battery state and returns the new one.
        Does not return until the update is done.
        """
        state = await self.core.device.battery.async_update_battery_state()
        self.write({"state": state[1], "charge": state[0]})

class NetworkHandler(BaseFeatureHandler):

    feature = FEATURES.FEATURE_NETWORK

    def _create_network_dict(self) -> dict:

        network = self.core.device.network
        conf = {
            "ip_address": network.IP,
            "mac_address": network.macAddress,
            "network_ssid": network.SSID,
            "signal": network.signal,
        }
        return conf
    
    def get(self):
        self.write(self.application.get_network_config())
        # self.write(self.application.get_net)

    async def post(self):
        """Updates the network state and returns the new one.
        Does not return until the update is done.
        """
        await self.core.device.network.async_update_network_properties()
        self.write(self.application.get_network_config())

class BacklightHandler(BaseFeatureHandler):

    feature = FEATURES.FEATURE_BACKLIGHT

    def get(self):

        self.write(self.application.get_backlight_config())
        return
        backlight = self.core.device.backlight
        conf = {
            "state": backlight.state,
            "brightness": backlight.brightness,
            "behaviour": backlight.behaviour,
            
            "default_time_on": backlight.default_time_on,
            "default_brightness": backlight.default_brightness,
            "default_transition": backlight.defaultTransition
        }
        self.write(conf)


class ActionsGetter(RequestHandler):
    "Returns a list of all registered shorthand actions (not action groups)"

    def get(self):
        self.write(self.application.get_actions_config())
        

class BaseActionHandler(RequestHandler):

    async def post(self, action: str):
        
        # if action not in self.application.
        #     self.send_error(404, reason = f"No Shorthand Action {action}")
        #     return

        # func = self.core.screen.shorthandFunctions[action]
        # ##Maybe wrap these in a very short wait, so some errors in the call can be caught out
        # ##But the entire function call is not awaited
        # coro = tools.wrap_to_coroutine(func, **self.json_args)
        
        try:
            func = self.application.parse_shorthand_action(action)
        except ShorthandNotFound:
            self.send_error(404, reason = f"No Shorthand Action {action}")
            return

        ##Not fully sure if this is fine like this?
        ##I.e. if it does allow throwing the argumenterror
        ##Test that
        try:
            tools.validate_action_call(func, keyword_arguments=self.json_args)
        except TypeError as exce:
            self.send_error(400, reason=f"{exce}")
            return

        coro = tools.wrap_to_coroutine(func, **self.json_args)
        (res, exce) = await self.application.run_coroutine(coro)
        if res == 200:
            self.write({"message": f"action {action} called"})
        else:
            self.send_error(res, reason=f"Could not call action {action}: {exce}")
        return


class ActionGroupHandler(RequestHandler):

    async def post(self, action_group: str, action: str):

        args = self.json_args.copy()
        data = args.pop("data", {})
        if action_group not in self.core.screen.shorthandFunctionGroups or action_group in self.application._removed_action_groups:
            self.send_error(404, reason = f"No shorthand action group {action_group} is registered")
            return
        
        try:
            func = self.application.parse_group_action(action_group, action, options=args)
        except ShorthandGroupNotFound:
            self.send_error(404, reason = f"No shorthand action group {action_group} is registered")
            return
        except ShorthandNotFound:
            self.send_error(404, reason = f"Shorthand action group {action_group} could not parse {action}")
            return
        
        try:
            tools.validate_action_call(func, keyword_arguments=data)
        except TypeError as exce:
            self.send_error(400, reason=f"{exce}")
            return
        
        coro = tools.wrap_to_coroutine(func, **data)
        
        (res, exce) = await self.application.run_coroutine(coro)
        if res:
            self.write({"message": f"action {action_group}:{action} called"})
        else:
            ##Handle errors a bit better ofc
            self.send_error(res, reason=f"Could not call action {action}: {exce}")
        return


def make_app(app: APICoordinator):
    # app = APICoordinator()
    app.add_handlers(r'(localhost|127\.0\.0\.1)',
        [
        (r"/api", MainHandler),    ##Main thing endpoint, returns text that the api is running
        (r"/api/config", ConfigGetter),
        
        (r"/api/device", DeviceHandler), ##Returns a list with all the features of the device, and the model and platform
        (r"/api/device/battery", BatteryHandler),
        (r"/api/device/network", NetworkHandler),
        (r"/api/device/backlight", BacklightHandler),
        
        (r"/api/actions", ActionsGetter),   ##Returns all available shorthand actions
        ##May group these two together. Since post and get are handled differently anyways?
        ##Can be rewritten, have the GET for actions return groups as well.
        (r"/api/actions/([a-z,-_]+)/([a-z,-_]+)", ActionGroupHandler),   ##Calls a shorthand action from a group. The "data" key from the body is passed to the function as keyword args
        (r"/api/actions/([a-z,-_]+)", BaseActionHandler),    ##Calls a shorthand action without identifier. body data is send as is to the function as keyword args
                    ])

    return app

##api endpoints to implement:
##device: features, info?
##screen -> get properties? maybe just a few basic ones i.e. screen size and color modes
##Also: getter for shorthand functions and getter for shorthand groups
##config -> not the full config, but info.
##i.e., inkBoard entry, integrations(?) base device info and screen info?
##integration list

##For device features:
##Some features (battery, backlight?) Should have a class that can both get and post (post simply calling the update method)

##screen info: mainelement (id), popupregister -> move to config
##Also include tab pages if appropriate

##device info: size, rotation, model, platform, deviceName, screentype; base info endpoint
##Add features for endpoints? Or in info?
##I.e. how to get the battery state, backlight state etc.

##Also: implement a websocket; can use the same setup
##Will require: all the implemented getters should be a function in the app which returns the required value.


async def main():
    app = make_app()
    app.listen(DEFAULT_PORT)
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.run(main())