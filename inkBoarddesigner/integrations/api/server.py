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

    @property
    def core(self) -> "CORE":
        return self._core
    
    @property
    def device(self) -> "BaseDevice":
        return self._core.device
    
    @property
    def server(self) -> tornado.httpserver.HTTPServer:
        return self._server

    def close_server(self):
        self

class RequestHandler(RequestHandler):

    application: inkBoardAPI

    @property
    def core(self) -> "CORE":
        return self.application.core
    
    def decode_body_arguments(self) -> dict[str,Union[str,int,float]]:
        """Decodes the arguments in the body to a dict.
        
        Returns an empty dict if the body is empty. 
        Arguments must be JSON.
        """
        if self.request.body:
            return tornado.escape.json_decode(self.request.body)
        else:
            return {}

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

    application: inkBoardAPI

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

class ActionsHandler(RequestHandler):
    "Returns a list of all registered shorthand actions (not action groups)"

    def get(self):
        self.write(tornado.escape.json_encode(
            list(self.core.screen.shorthandFunctions.keys())))

class BaseActionHandler(RequestHandler):

    async def post(self, action: str):
        
        if action not in self.core.screen.shorthandFunctions:
            self.send_error(400, missing_action = action)
            return

        func = self.core.screen.shorthandFunctions[action]
        await tools.wrap_to_coroutine(func, **self.decode_body_arguments())
        return
    
    def write_error(self, status_code, **kwargs):
        if status_code == 400 and "missing_action" in kwargs:
            self.write(f"{status_code}: No Shorthand Action {kwargs['missing_action']}")
        else:
            return super().write_error(status_code, **kwargs)

class ActionGroupHandler(RequestHandler):

    async def post(self, action_group: str, action: str):

        args = self.decode_body_arguments()
        data = args.pop("data", {})
        if action_group not in self.core.screen.shorthandFunctionGroups:
            self.send_error(400, f"No shorthand action group {action_group} is registered")
            return
        
        try:
            func = self.core.screen.parse_shorthand_function(f"{action_group}:{action}", options=args)
        except ShorthandGroupNotFound:
            self.send_error(400, f"No shorthand action group {action_group} is registered")
            return
        except ShorthandNotFound:
            self.send_error(400, f"Shorthand action group {action_group} could not parse {action}")
            return
        
        await tools.wrap_to_coroutine(func, **data)
        return
    
    def write_error(self, status_code, **kwargs):
        if status_code == 400 and "action_error_string" in kwargs:
            self.write(f"{status_code}: {kwargs['action_error_string']}")
        else:
            return super().write_error(status_code, **kwargs)

def make_app():
    app = inkBoardAPI()
    app.add_handlers(r'(localhost|127\.0\.0\.1)',
        [(r"/api", MainHandler),
        (r"/api/device/features", DeviceFeaturesHandler),
        (r"/api/actions", ActionsHandler),
        (r"/api/action/([a-z,-_]+)/([a-z,-_]+)", ActionGroupHandler),
        (r"/api/action/([a-z,-]+)", BaseActionHandler),
                    ])

    return app

##api endpoints to implement:
##device: features, a get_feature thingy
##screen -> get properties? maybe just a few basic ones i.e. screen size and color modes
##Also: getter for shorthand functions and getter for shorthand groups
##config
##integration list

##actions: action that routes to shorthands

async def main():
    app = make_app()
    app.listen(DEFAULT_PORT)
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.run(main())