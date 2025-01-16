"""Module holding the base coordinator for the inkBoard API

"""
from typing import *
from types import MappingProxyType
import asyncio
from functools import cached_property

import tornado

import inkBoard
from inkBoard import core as CORE
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

class removeaccessdict(TypedDict):
    actions: list[str]
    action_groups: list[str]
    group_actions: dict[str,list[str]]

class APICoordinator(tornado.web.Application):

    def __init__(self, 
                port: int = DEFAULT_PORT,
                remove_access : dict = {},
                allowed_networks : list[str] = []
                
                ):
        super().__init__(handlers=None, default_host=None, transforms=None)

        self._removed_shorthand_actions = set()
        self._removed_action_groups = set()
        self._removed_group_actions : dict[str,set] = {}

        self._setup_config_access(**remove_access)
        
        if allowed_networks == None: allowed_networks = [None]
        assert isinstance(allowed_networks, Sequence), "allowed_networks must be a list"
        self._allowed_networks = allowed_networks
        self._port = port

        return

    #region
    @property
    def core(self) -> "CORE":
        return self._core
    
    @property
    def device(self) -> "BaseDevice":
        return self._core.device
    
    @property
    def server(self) -> tornado.httpserver.HTTPServer:
        return self._server

    @property
    def baseConfig(self) -> MappingProxyType:
        """Returns a base config of the inkBoard instance

        This config is, for example, returned via the ``/api/config`` endpoint.
        Does not yet include the ``main_element`` and ``popups`` entries.
        """

        conf = {}
        conf["name"] = self.core.config.inkBoard.name

        conf["start_time"] = self.core.IMPORT_TIME
        conf["platform"] = self.core.device.platform
        conf["version"] = inkBoard.__version__

        conf["integrations"] = tuple(self.core.integration_loader.imported_integrations.keys())
        return conf
    #endregion

    def _setup_config_access(self, 
                            actions : list = [], 
                            action_groups : list = [],
                            group_actions : dict = {}):
        ##Used to setup api access at init

        for action in actions:
            self.remove_action_access(action)
        
        for group in action_groups:
            self.remove_action_group_access(group)

        for group, actions in group_actions:
            for action in actions:
                self.remove_group_action_access(group, action)

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
        ##Functions/properties to add:
        # base config (as cached property)
        # base device config -> only holding features that do not change
        # battery, network getter, etc.
        # action and action group getter
        # also add a request that will start log streaming; eh seems to not be the way
        # do include a logging_port in the base config

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

        if (action not in self.core.screen.shorthandFunctionGroups
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
            ##Gather the page id's from the element.
            ##Also: add current tab in info as well as optional popup that is on top
        
        conf["popups"] = {
            "current_popup": self.core.screen.popupsOnTop[-1] if self.core.screen.popupsOnTop else None,
            "registered_popups": list(self.core.screen.popupRegister.keys())
        }
        return conf
    
    def get_device_config(self) -> dict:

        device = self.core.device
        conf = {
            "platform": device.platform,
            "model": device.model,
            "name": device.name,
            "size": (device.screenWidth, device.screenHeight),
            "screen_type": device.screenType,
            "screen_mode": device.screenMode
            }
        
        if device.has_feature(FEATURES.FEATURE_ROTATION):
            conf["rotation"] = device.rotation

        features = []
        for feat, val in device._features._asdict().items():
            if val: features.append(feat)
        
        conf["features"] = features
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
    
    
    def get_battery_config(self):
        ##Add error class to handle missing features
        return