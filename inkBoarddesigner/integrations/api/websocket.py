
from typing import *
import json


from tornado.websocket import WebSocketHandler

if TYPE_CHECKING:
    from .app import APICoordinator


class inkBoardWebSocket(WebSocketHandler):

    async def open(self):
        print("WebSocket opened")
        self.write_message({"type": "connection", "message": "connected to inkBoard"})

    async def on_message(self, message):
        
        try:
            message_conf = json.loads(message)
        except json.JSONDecodeError:
            self.write_message({"type": "error", "message": "message must be valid json"})
            return
        

        self.write_message(u"You said: " + message)

    def on_close(self):
        print("WebSocket closed")

    pass


def make_app(app: "APICoordinator"):

    app.add_handlers(r'(localhost|127\.0\.0\.1)',
                    [(r"/api/websocket", inkBoardWebSocket)]
    )
    return