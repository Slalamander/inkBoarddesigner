"""Module holding the base coordinator for the inkBoard API

"""
from typing import *
import asyncio
from functools import cached_property, wraps
from contextlib import suppress
import json
import ssl

import tornado
from tornado.escape import json_encode as tornado_json_encode

import inkBoard
from inkBoard import CORE as CORE
from inkBoard.constants import DEFAULT_MAIN_TABS_NAME

import PythonScreenStackManager
from PythonScreenStackManager import tools
from PythonScreenStackManager.exceptions import ShorthandNotFound, ShorthandGroupNotFound
from PythonScreenStackManager.elements import Element, TabPages
from PythonScreenStackManager.pssm.util import ElementJSONEncoder

from .constants import DEFAULT_PORT, DEFAULT_HOST_PATTERN

from .apitypes import *

if TYPE_CHECKING:
    from inkBoard import CORE as CORE
    from inkBoard.platforms import BaseDevice
    from PythonScreenStackManager.pssm import PSSMScreen
    from .websocket import inkBoardWebSocket

_LOGGER = inkBoard.getLogger(__name__)

ssl_ctx = ssl.SSLContext()

class _ALLOW_NONE:
    pass

@wraps(tornado_json_encode)
def json_encode_message(value):

    return json.dumps(value, cls=ElementJSONEncoder).replace("</", "<\\/")


tornado.escape.json_encode = json_encode_message


##Functions/properties to add:
# do include a logging_port in the base config

class APICoordinator(tornado.web.Application):

    def __init__(self, core: "CORE",
                port: int = DEFAULT_PORT,
                restapi: bool = True, websocket: bool = True,
                remove_access : removeaccessdict = {},
                allowed_networks : list[str] = [], host_pattern : str = DEFAULT_HOST_PATTERN
                ):
        super().__init__(handlers=None, default_host=None, transforms=None)

        self._core = core

        self._removed_shorthand_actions = set()
        self._removed_action_groups = set()
        self._removed_group_actions : dict[str,set] = {}

        self._setup_config_access(**remove_access)
        
        if isinstance(allowed_networks,str): allowed_networks = [allowed_networks]
        if allowed_networks == None: allowed_networks = [_ALLOW_NONE]
        assert isinstance(allowed_networks, Sequence), "allowed_networks must be a list"
        self._allowed_networks = allowed_networks
        self._port = port
        self._host_pattern = host_pattern

        self._server = None
        self._enabledCondition = asyncio.Condition()

        self._websockets: set["inkBoardWebSocket"] = set()

        if restapi:
            from .restapi import add_restapi_handlers
            add_restapi_handlers(self)

        if websocket:
            from .websocket import add_websocket_handler
            add_websocket_handler(self)

        return

    #region
    @property
    def core(self) -> "CORE":
        return self._core
    
    @property
    def device(self) -> "BaseDevice":
        return self.core.device
    
    @property
    def screen(self) -> "PSSMScreen":
        return self.core.screen

    @property
    def enabled(self) -> bool:
        """Indicates if the API is currently enabled

        Indicates if the API server is currently open and being listened to.
        Does NOT indicate if the API is enabled from the config, for that check the config for the ``api`` key. 
        """
        return self._server != None

    @property
    def enabledCondition(self) -> asyncio.Condition:
        """async condition that is notified when the state of enabled changes
        This condition being notified means the server has either been closed or been opened.
        """
        return self._enabledCondition

    @property
    def baseConfig(self) -> dict:
        """Returns a base config of the inkBoard instance

        This config is, for example, returned via the ``/api/config`` endpoint.
        Does not yet include the ``main_element`` and ``popups`` entries.
        """

        conf = {}
        conf["name"] = self.core.config.inkBoard.name

        conf["start_time"] = self.core.IMPORT_TIME
        conf["platform"] = self.core.device.platform
        conf["version"] = inkBoard.__version__

        conf["integrations"] = tuple(self.core.integrationLoader.imported_integrations.keys())
        return conf
    #endregion

    def _setup_config_access(self, 
                            actions : list = [], 
                            action_groups : list = [],
                            group_actions : dict = {}):

        for action in actions:
            self.remove_action_access(action)
        
        for group in action_groups:
            self.remove_action_group_access(group)

        for group, actions in group_actions:
            for action in actions:
                self.remove_group_action_access(group, action)

    async def listen(self):

        await self._handle_network_ssid()
        condition = self.screen.deviceUpdateCondition
        network = self.device.network.SSID
        while self.core.screen.printing:
            with suppress(asyncio.CancelledError):
                async with condition:
                    await condition.wait_for(lambda : network != self.device.network.SSID)
                _LOGGER.debug(f"Device network changed from {network} to {self.device.network.SSID}, checking if allowed")
            await self._handle_network_ssid()
            network = self.device.network.SSID

    async def _handle_network_ssid(self) -> bool:

        network = self.device.network.SSID
        if (self.device.network.connected and
            (len(self._allowed_networks) == 0 or
            network in self._allowed_networks)):
            if not self._server:
                self._server = super().listen(self._port, ssl_options = ssl_ctx)
            else:
                return
        else:
            if self._server:
                self._server.stop()
                await self._server.close_all_connections()
                self._server = None
            else:
                return
        async with self.enabledCondition:
            self.enabledCondition.notify_all()

    async def stop(self):
        if self._server:
            _LOGGER.info("Closing all sockets")
            self._server.stop()
            await self._server.close_all_connections()
            _LOGGER.info("Closed all api connections")

    def remove_action_access(self, action: str):
        """Prevents an action shorthand from being callable via the api

        This will throw a 404 error if the action is called

        Parameters
        ----------
        action : str
            The action to remove
        """
        self._removed_shorthand_actions.add(action)

    def remove_action_group_access(self, action_group: str):
        """Prevents an action group from being callable via the api

        This will throw a 404 error if the group is called.

        Parameters
        ----------
        action_group : str
            The action group to remove
        """
        self._removed_action_groups.add(action_group)

    def remove_group_action_access(self, group: str, action: str):

        if group in self._removed_action_groups:
            self._removed_group_actions[group].add(action)
        else:
            self._removed_group_actions[group] = set([action])

    def parse_shorthand_action(self, action: str) -> Callable:
        """Gets a shorthand action from the screen's registery

        Prevent any actions removed from access from being returned

        Parameters
        ----------
        action : str
            The shorthand action to retrieve

        Returns
        -------
        Callable
            The function represented by the shorthand

        Raises
        ------
        ShorthandNotFound
            Indicates the shorthand does not exist or is barred from api access
        """        

        if (action not in self.core.screen.shorthandFunctions
            or action in self._removed_shorthand_actions):
            raise ShorthandNotFound(action)
        
        return self.core.screen.shorthandFunctions[action]
    
    def parse_group_action(self, group: str, action: str, options: dict) -> Callable:
        """Gets a shorthand function from a function group

        The shorthand passed to the parser is {group}:{action}

        Parameters
        ----------
        group : str
            The group to retrieve the action from, i.e. the identifier when parsing in YAML
        action : str
            The action to retrieve
        options : dict
            Options to pass to the parser

        Returns
        -------
        Callable
            The function represented by the shorthand

        Raises
        ------
        ShorthandGroupNotFound
            Indicates the shorthand group does not exist or is barred from api access
        ShorthandNotFound
            Indicates the shorthand does not exist or is barred from api access
        """

        if (group not in self.core.screen.shorthandFunctionGroups
            or group in self._removed_action_groups):
            raise ShorthandGroupNotFound(group)
        
        if (group in self._removed_group_actions
            and action in self._removed_group_actions[group]):
            raise ShorthandNotFound(action)
        
        return self.core.screen.parse_shorthand_function(f"{group}:{action}", options=options)

    async def run_coroutine(self, coro: Coroutine) -> tuple[int,Union[None,Exception]]:
        """Starts running the provided coroutine

        This function returns almost immediately, but the coroutine will keep running.
        It is meant to catch out errors in function paramaters.

        Parameters
        ----------
        coro : Coroutine
            The coroutine to run

        Returns
        -------
        tuple[int, Exception | None]
            An appropriate return code, and optionally the exception thrown, if any.
        """

        res = ()
        t = asyncio.create_task(coro)

        return (200, None)

    def get_elements(self) -> dict:
        "Returns a dict with all registered elements and their type"
        elt_dict = {}
        for elt_id, elt in self.screen.elementRegister.items():
            if elt.__module__.startswith(("PythonScreenStackManager.elements","abc")):
                type_ = elt.__class__.__name__
            elif elt.__module__.startswith("inkBoard.integrations"):
                type_ = elt.__module__.lstrip("inkBoard.integrations.")
            else:
                type_ = f"{str(elt.__module__)}.{elt.__class__.__name__}"
            elt_dict[elt_id] = type_
        
        return elt_dict
        
    def get_rest_config(self) -> dict:

        conf = self.baseConfig
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

        conf["popups"] = {
            "current_popup": self.core.screen.popupsOnTop[-1].id if self.core.screen.popupsOnTop else None,
            "registered_popups": list(self.core.screen.popupRegister.keys())
        }
        return conf
    
    def get_device_config(self) -> dict:

        device = self.core.device
        conf = {
            "platform": device.platform,
            "model": device.model,
            "name": device.name,
            "screen_type": device.screenType,
            "screen_mode": device.screenMode
            }
        
        conf["features"] = device.features
        return conf
    
    def get_shorthand_actions(self) -> tuple[str]:
        """All shorthand actions accessible by the API

        Returns
        -------
        tuple
            tuple with accessible shorthand actions
        """

        return tuple(set(self.core.screen.shorthandFunctions.keys()) - self._removed_shorthand_actions)
    
    def get_shorthand_action_groups(self) -> tuple[str]:
        """All shorthand action groups accessible by the API

        Returns
        -------
        tuple[str]
            tuple with accessible shorthand groups
        """

        return tuple(set(self.core.screen.shorthandFunctionGroups.keys()) - self._removed_action_groups)
    
    def get_actions_config(self) -> actionsconfig:
        conf = {"shorthands": self.get_shorthand_actions(),
                "groups": self.get_shorthand_action_groups()}
        return conf
    
    def get_battery_config(self) -> batteryconfig:
        ##Add error class to handle missing features
        conf = self.device.battery.get_feature_state()
        return conf
    
    def get_network_config(self) -> networkconfig:
        conf = self.device.network.get_feature_state()
        conf = {
            "ip_address": conf["IP"],
            "mac_address": self.device.network.macAddress,
            "network_ssid": conf["SSID"],
            "signal": conf["signal"]
        }
        return conf
    
    def get_backlight_config(self) -> backlightconfig:
        conf = self.device.backlight.get_feature_state()
        return conf
    
    ##Add function for screen state (to get i.e. if a batch is running, top element in stack etc.)
    
