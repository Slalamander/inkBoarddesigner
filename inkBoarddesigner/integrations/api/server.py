"Sets up the api server for inkBoard"

from typing import *
import json

from dataclasses import asdict

import asyncio
import tornado
from tornado.web import RequestHandler

from inkBoard.platforms import InkboardDeviceFeatures

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


def make_app():
    return inkBoardAPI([
        (r"/api", MainHandler),
        (r"/api/device/features", DeviceFeaturesHandler)
    ])

##api endpoints to implement:
##device: features, a get_feature thing
##screen
##config

##actions: action that routes to shorthands

async def main():
    app = make_app()
    app.listen(DEFAULT_PORT)
    shutdown_event = asyncio.Event()
    await shutdown_event.wait()

if __name__ == "__main__":
    asyncio.run(main())