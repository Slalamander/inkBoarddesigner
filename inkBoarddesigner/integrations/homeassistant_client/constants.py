"""
Constants for use with the HA PSSM library
"""
from typing import Literal, Optional, Union
import yaml

from PythonScreenStackManager.constants import INKBOARD, PSSM_COLORS, SHORTHAND_FONTS, SHORTHAND_ICONS 
from pathlib import Path

import logging

logger = logging.getLogger(__name__)

__default_domain_actions: dict[Literal["domain"],Optional[Literal["action"]]] = {  
                        "default": None,
                        "switch": "switch.toggle",
                        "light": "light.toggle",
                        "button": "button.press",
                        "climate": "climate.toggle",
                        "fan": "fan.toggle",
                        "media_player": "media_player.toggle",
                        "remote": "remote.toggle",
                        "scene": "scene.turn_on",
                        "select": "select.next", ##For this one, cycle should be set to true automatically...
                        
                        "automation": "automation.trigger",
                        "script": "script.turn_on",
                        
                        "input_button": "input_button.press",
                        "input_boolean": "input_boolean.toggle",
                        "input_select": "input_select.select_next"
                        }

DEFAULT_DOMAIN_ACTIONS = __default_domain_actions
"""
Dict mapping certain HA domains to default actions that can be applied to elements without entity domain restrictions.
Domains without a default action are not present in this dict.
"""

ENTITY_TAG_KEY = "!entity "

DEFAULT_HA_DT_FORMAT = "%Y-%m-%-dT%H:%M:%S.%Y+%H:%M"
"""
The default format Home Assistant seems to use for datetime strings.
Parsing this using `datetime.strptime()` throws an error, however it does work when using `datetime.fromisoformat()`
That means this constant is likely not necessary anywhere, but leaving it here in case.
"""

DEFAULT_PING_INTERVAL : int = 50 #seconds
"Default time in seconds to send a new ping"

MAX_PONGS_MISSED : int = 5
"Max amount of pongs to be missed before the connection is considered broken."

HOMEASSISTANT_BLUE : tuple = (3, 169, 244, 255)
"The Blue Color used in Home Assistant Branding :)"

HOMEASSISTANT_ICON = Path(__file__).parent / 'home-assistant.png'

ERROR_STATES = {"unknown", "unavailable"}
"Shorthand for the states that indicate an error in the entity (so unknown or unavailable)"

UNKNOWN_ICON = "mdi:help"
"Default icon for unknown states"

UNAVAILABLE_ICON = "mdi:exclamation-thick"
"Default icon for unavailable states"

UNAVAILABLE_COLOR = "gray4"
"Color to use for text elements when the entity state is unavailable"

UNKNOWN_COLOR = "gray4"
"Color to use for text elements when the entity state is unknown"


# cf = CORE.config.configuration["home_assistant"]
# if "unavailable_color" in cf:
#     UNAVAILABLE_COLOR = cf["unavailable_color"]

# if "unknown_color" in cf:
#     UNKNOWN_COLOR = cf["unknown_color"]

# if "unavailable_icon" in cf:
#     UNAVAILABLE_ICON = cf["unavailable_icon"]

# if "unknown_icon" in cf:
#     UNKNOWN_ICON = cf["unknown_icon"]

# if "ping_pong_interval" in cf:
#     DEFAULT_PING_INTERVAL = cf["ping_pong_interval"]
