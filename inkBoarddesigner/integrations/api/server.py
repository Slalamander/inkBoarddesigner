"Sets up the api server for inkBoard"

from typing import *
import json

from dataclasses import asdict

import asyncio
import tornado
from tornado.web import RequestHandler

from inkBoard.platforms import InkboardDeviceFeatures
from PythonScreenStackManager import tools
from PythonScreenStackManager.exceptions import ShorthandNotFound, ShorthandGroupNotFound

from .constants import DEFAULT_PORT

if TYPE_CHECKING:
    from inkBoard import core as CORE
    from inkBoard.platforms import BaseDevice

class inkBoardAPI(tornado.web.Application):

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

    application: inkBoardAPI

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

class DeviceFeaturesHandler(RequestHandler):
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
        
        self.write(tornado.escape.json_encode(resp_dict))

class ActionsGetter(RequestHandler):
    "Returns a list of all registered shorthand actions (not action groups)"

    def get(self):
        actions = set(self.core.screen.shorthandFunctions.keys()) - self.application._removed_actions
        self.write(tornado.escape.json_encode(
                    list(actions)))
        
class ActionGroupsGetter(RequestHandler):
    "Returns a list of all registered shorthand actions (not action groups)"

    def get(self):
        groups = set(self.core.screen.shorthandFunctionGroups.keys()) - self.application._removed_action_groups
        self.write(tornado.escape.json_encode(
                    list(groups)))
        

class BaseActionHandler(RequestHandler):

    async def post(self, action: str):
        
        if action not in self.core.screen.shorthandFunctions or action in self.application._removed_actions:
            self.send_error(404, missing_action = action)
            return

        func = self.core.screen.shorthandFunctions[action]
        await tools.wrap_to_coroutine(func, **self.json_args)
        return
    
    def write_error(self, status_code, **kwargs):
        if status_code == 404 and "missing_action" in kwargs:
            self.write(f"{status_code}: No Shorthand Action {kwargs['missing_action']}")
        else:
            return super().write_error(status_code, **kwargs)

class ActionGroupHandler(RequestHandler):

    async def post(self, action_group: str, action: str):

        args = self.json_args.copy()
        data = args.pop("data", {})
        if action_group not in self.core.screen.shorthandFunctionGroups or action_group in self.application._removed_action_groups:
            self.send_error(400, f"No shorthand action group {action_group} is registered")
            return
        
        try:
            func = self.core.screen.parse_shorthand_function(f"{action_group}:{action}", options=args)
        except ShorthandGroupNotFound:
            self.send_error(404, f"No shorthand action group {action_group} is registered")
            return
        except ShorthandNotFound:
            self.send_error(404, f"Shorthand action group {action_group} could not parse {action}")
            return
        
        await tools.wrap_to_coroutine(func, **data)
        return
    
    def write_error(self, status_code, **kwargs):
        if status_code == 404 and "action_error_string" in kwargs:
            self.write(f"{status_code}: {kwargs['action_error_string']}")
        else:
            return super().write_error(status_code, **kwargs)

def make_app():
    app = inkBoardAPI()
    app.add_handlers(r'(localhost|127\.0\.0\.1)',
        [(r"/api", MainHandler),    ##Main thing endpoint, returns text that the api is running
        (r"/api/device/features", DeviceFeaturesHandler), ##Returns a list with all the features of the device, and the model and platform
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