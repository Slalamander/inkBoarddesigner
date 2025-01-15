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

    application: inkBoardAPIServer

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
    def get(self):
        self.write("API running")


class ConfigGetter(RequestHandler):

    def get(self):

        conf = {}
        conf["name"] = self.core.config.inkBoard.name

        if self.core.config.inkBoard.main_element:
            id = self.core.config.inkBoard.main_element
            elt = self.core.screen.elementRegister[id]

            if elt.__module__.startswith("PythonScreenStackManager.elements"):
                type_ = elt.__module__.split(".")[-1]
            elif elt.__module__.startswith("inkBoard.integrations"):
                type_ = elt.__module__.lstrip("inkBoard.integrations.")
            else:
                type_ = elt.__module__

            conf["main_element"] = {
                "id": id,
                "type": type_
            }
        elif "main_tabs" in self.core.config:
            conf["main_element"] = {
                "id": self.core.config["main_tabs"].get("id", DEFAULT_MAIN_TABS_NAME),
                "type": TabPages.__name__
            }
        else:
            conf["main_element"] = None

        conf["integrations"] = tuple(self.core.integration_loader.imported_integrations.keys())
        conf["start_time"] = self.core.IMPORT_TIME
        conf["platform"] = self.core.device.platform
        conf["version"] = inkBoard.__version__
        self.write(conf)

class DeviceFeaturesGetter(RequestHandler):
    """Returns a list with the device's features

    Parameters
    ----------
    RequestHandler : _type_
        _description_
    """

    async def get(self):
        resp_dict = {
            "platform": self.application.device.platform,
            "model": self.application.device.model,
            }

        features = []
        for feat, val in self.application.device._features._asdict().items():
            if val: features.append(feat)
        
        resp_dict["features"] = features
        
        self.write(resp_dict)

# class FeatureHandler

class BatteryHandler(RequestHandler):

    def prepare(self):
        if not self.core.device.has_feature(FEATURES.FEATURE_BATTERY):
            self.send_error(404, reason = "device does not have the battery feature")
            return
        return super().prepare()

    def get(self):
        conf = {
            "state": self.core.device.battery.state,
            "charge": self.core.device.battery.charge
        }
        self.write(conf)

    async def post(self):
        state = await self.core.device.battery.async_update_battery_state()
        self.write({"state": state[1], "charge": state[0]})

class NetworkHandler(RequestHandler):

    def prepare(self):
        if not self.core.device.has_feature(FEATURES.FEATURE_NETWORK):
            self.send_error(404, reason = "device does not have the network feature")
            return

    def _create_network_dict(self) -> dict:

        network = self.core.device.network
        conf = {
            "ip_adress": network.IP,
            "mac_adress": network.macAddr,
            "network_ssid": network.SSID,
            "signal": network.signal,
        }
        return conf
    
    def get(self):
        self.write(self._create_network_dict())

    async def post(self):
        await self.core.device.network.async_update_network_properties()
        self.write(self._create_network_dict())

class ActionsGetter(RequestHandler):
    "Returns a list of all registered shorthand actions (not action groups)"

    def get(self):
        actions = set(self.core.screen.shorthandFunctions.keys()) - self.application._removed_actions
        self.write(list(actions))
        
class ActionGroupsGetter(RequestHandler):
    "Returns a list of all registered shorthand actions (not action groups)"

    def get(self):
        groups = set(self.core.screen.shorthandFunctionGroups.keys()) - self.application._removed_action_groups
        self.write(list(groups))
        

class BaseActionHandler(RequestHandler):

    async def post(self, action: str):
        
        if action not in self.core.screen.shorthandFunctions or action in self.application._removed_actions:
            self.send_error(404, reason = f"No Shorthand Action {action}")
            return

        func = self.core.screen.shorthandFunctions[action]
        await tools.wrap_to_coroutine(func, **self.json_args)
        return


class ActionGroupHandler(RequestHandler):

    async def post(self, action_group: str, action: str):

        args = self.json_args.copy()
        data = args.pop("data", {})
        if action_group not in self.core.screen.shorthandFunctionGroups or action_group in self.application._removed_action_groups:
            self.send_error(404, reason = f"No shorthand action group {action_group} is registered")
            return
        
        try:
            func = self.core.screen.parse_shorthand_function(f"{action_group}:{action}", options=args)
        except ShorthandGroupNotFound:
            self.send_error(404, reason = f"No shorthand action group {action_group} is registered")
            return
        except ShorthandNotFound:
            self.send_error(404, reason = f"Shorthand action group {action_group} could not parse {action}")
            return
        
        await tools.wrap_to_coroutine(func, **data)
        return


def make_app():
    app = inkBoardAPIServer()
    app.add_handlers(r'(localhost|127\.0\.0\.1)',
        [
        (r"/api", MainHandler),    ##Main thing endpoint, returns text that the api is running
        (r"/api/config", ConfigGetter),
        
        (r"/api/device/features", DeviceFeaturesGetter), ##Returns a list with all the features of the device, and the model and platform
        (r"/api/device/battery", BatteryHandler),
        (r"/api/device/network", NetworkHandler),
        
        (r"/api/actions", ActionsGetter),   ##Returns all available shorthand actions
        (r"/api/actions/groups", ActionGroupsGetter),   ##Returns all available action groups

        (r"/api/action/([a-z,-_]+)/([a-z,-_]+)", ActionGroupHandler),   ##Calls a shorthand action from a group. The "data" key from the body is passed to the function as keyword args
        (r"/api/action/([a-z,-_]+)", BaseActionHandler),    ##Calls a shorthand action without identifier. body data is send as is to the function as keyword args
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

##screen info: size, rotation, mainelement (id), popupregister, 
##device info: size, rotation, model, platform, deviceName, screentype; base info endpoint
##Add features for endpoints? Or in info?
##I.e. how to get the battery state, backlight state etc.

##actions: action that routes to shorthands

async def main():
    app = make_app()
    app.listen(DEFAULT_PORT)
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.run(main())