"Sets up the api server for inkBoard"

from typing import *
import json

from dataclasses import asdict

import asyncio
import tornado
from tornado.web import RequestHandler

import inkBoard
from inkBoard.platforms.basedevice import FEATURES
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

class DeviceHandler(RequestHandler):
    """Returns a list with the device's features
    """

    async def get(self):
        conf = self.application.get_device_config()
        conf["size"] = self.core.device.screenSize
        if self.core.device.has_feature(FEATURES.ROTATION):
            conf["rotation"] = self.core.device.rotation
        else:
            conf["rotation"] = None

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

class ActionsGetter(RequestHandler):
    "Returns a list of all registered shorthand actions (not action groups)"

    def get(self):
        self.write(self.application.get_actions_config())
        

class BaseActionHandler(RequestHandler):

    async def post(self, action: str):
        
        try:
            func = self.application.parse_shorthand_action(action)
        except ShorthandNotFound:
            self.send_error(404, reason = f"No Shorthand Action {action}")
            return

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
            self.send_error(res, reason=f"Could not call action {action}: {exce}")
        return


def add_restapi_handlers(app: APICoordinator):

    app.add_handlers(app._host_pattern,
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

