##HomeAssistantClient file
"""
This library manages elements from PSSM and linked entities from Home Assistant, and provides additional comound elements in the HAelements library.
Import it first, or at least before importing the element library to allow it to add to the PSSM default colors and fonts.
"""
from __future__ import annotations
from typing import Literal, TypedDict, TypeVar, Optional, Union, TYPE_CHECKING
from pathlib import Path
from string import Template
import asyncio
from io import BytesIO
import logging

import requests
from PIL import Image

from .constants import ENTITY_TAG_KEY

if TYPE_CHECKING:
    from inkBoard import core as CORE

_LOGGER = logging.getLogger(__name__)

##Use this file to declare some more constants and extend a couple
class DomainError(ValueError):
    "The supplied entity is not of a valid domain."
    pass

##Mind the docstring when dealing with errors here (i.e. use from fromisoformat)

HAtimestrFormat = Literal["%Y-%m-%-dT%H:%M:%S.%Y+%H:%M"] #Literal[DEFAULT_HA_DT_FORMAT]
"Default Home Assistant datetime string typing"

EntityType = TypeVar("entity_id", bound=str)

stateDictType = TypedDict('stateDict', {"entity_id":str, "state": str, "attributes": dict, "last_changed": HAtimestrFormat,"last_reported": HAtimestrFormat, "last_updated": HAtimestrFormat, "context": dict})
"Typed dict for an entities state as passed from a trigger"

triggerDictType = TypedDict('triggerDictType',{"entity_id":str,"to_state": stateDictType, "from_state": Optional[stateDictType], "context":Optional[dict]})
"Typed dict for how triggers are passed"


actionCallDict = TypedDict('actionCallDict', {"id": int, "type": str, "domain": str, "service":str, "service_data": dict, "target": dict, "return_response": bool}, total=True)
"Typed dict for the message format of a HA action call via the websocket"

actionCallDict.__optional_keys__ = frozenset({"service_data", "target"})
actionCallDict.__required_keys__ = actionCallDict.__required_keys__.difference(actionCallDict.__optional_keys__)

serviceCallDict = actionCallDict

WeatherData = Literal["datetime", "cloud_coverage", "condition", "humidity", "temperature", "apparent_temperature", "dew_point", "pressure", "visibility", "wind_gust_speed", "wind_speed", "ozone", "uv_index", "wind_bearing"]
"Type hint with (most likely) all possible weather data in a weather entity's attributes."

_all_entities = {}
_substitutions = {}
_all_service_actions = {}

async def request_image_threadsafe(image_url : str) -> tuple[Union[Image.Image, requests.Response],int]: #Union[tuple[Image.Image,Literal["status_code"]],tuple[requests.Response, Literal["status_code"]]]:    
    """
    Gets an image from a request.get response in a non-blocking manner.
    Method from: https://superfastpython.com/python-async-requests/

    Parameters
    ----------
    image_url : str
        url to get the image from

    Returns
    -------
    tuple[Image.Image | requests.response, status_code] | 
        If the status code is 200 (i.e. the request was succesfull) a tuple is returned with the gotten Image and the status code. 
        Otherwise a tuple with the full response and the status code is returned.
    """
    try:
        response = await asyncio.to_thread(requests.get, image_url)
    except (requests.exceptions.InvalidURL):
        _LOGGER.error(f"Cannot request image from {image_url}, invalid url")
        return (None, -1)

    if response.status_code == 200:

        ##Is this one threadsafe? Since it's not technically reading a file I'm not sure 
        ##Replaced it with a to_thread call to be sure
        # img = Image.open(BytesIO(response.content))
        respIO = BytesIO(response.content)
        img = await asyncio.to_thread(Image.open,respIO)
        return (img.copy(), response.status_code)
    else:
        _LOGGER.warning(f"Unable to get requested image")
        return (response, response.status_code)
    
def _gather_entities_and_actions(core: "CORE"):
    """Gathers all entities from the configuration (and optionally adds sun.sun)

    Parameters
    ----------
    core : CORE
        inkBoard core object
    """

    _all_entities.clear()
    _substitutions.clear()
    _all_service_actions.clear()

    _all_entities["sun.sun"] = {"entity_id": "sun.sun"}

    all_entities_config = core.config.configuration.get("entities",{}).copy()

    for entity_config in all_entities_config:
        if "entity_id" not in entity_config:
            _LOGGER.error(f"Entries in the entity config require an entity_id. Cannot add {entity_config}")
        else:
            _all_entities[entity_config["entity_id"]] = entity_config

    for subst, val in core.config.substitutions.items():
        _substitutions[subst] = val

    _all_services_config = core.config.configuration.get("service_actions",{}).copy()
    for service_config in _all_services_config:
        if "service_id" not in service_config:
            _LOGGER.error(f"Entries in the service_actions config require a service_id. Cannot add {service_config}")
        else:
            _all_service_actions[service_config["service_id"]] = service_config
    return _all_entities, _all_service_actions


def parse_entity_tag(entity : str) -> Union[str,Literal[False]]:
    """Parses a tagged entity from the config's substitutions

    Substitutions work the same as in the configuration, i.e. via a ${my_substitution}
    Entity can also be prefixeded by ``!entity `` after which the substitution key should follow.

    Parameters
    ----------
    entity : str
        The string to substitute

    Returns
    -------
    Union[str,Literal[False]]
        The parsed entity or substitution, or False if none could be parsed.
    """    

    if entity.startswith(ENTITY_TAG_KEY):
        tag = entity.removeprefix(ENTITY_TAG_KEY)
        
        if tag not in _substitutions:
            msg = f"{tag} could not be found as a key in the entities.yaml file. "
            _LOGGER.exception(KeyError(msg))
            return False
        else:
            return _substitutions[tag]
    elif entity.startswith("$"):
        try:
            return Template(entity).substitute(**_substitutions)
        except KeyError:
            _LOGGER.error(f"No substition for {entity}")
            return False
