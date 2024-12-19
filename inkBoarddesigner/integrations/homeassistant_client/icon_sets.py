"""
Holds data for default icon packs for some elements.
"""
import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

from inkBoard.constants import DESIGNER_INSTALLED
from PythonScreenStackManager.constants import MDI_WEATHER_DATA_ICONS, PATH_TO_PSSM
from mdi_pil import MDI_WEATHER_ICONS as MDI_WEATHER_CONDITION_ICONS

if TYPE_CHECKING:
    from .. import meteocons

METEOCONS_INSTALLED: bool = False
s = importlib.util.find_spec("inkBoard.integrations.meteocons")
if DESIGNER_INSTALLED:
    try:
        s = importlib.util.find_spec("inkBoarddesigner.integrations.meteocons")
    except:
        pass

if s:
    METEOCONS_INSTALLED = True
    METEOCONS = importlib.import_module(s.name)

##Should be able to parse from both inkBoard or designer integration.

HVAC_MODES_ICONS : dict = {
    "off" : "mdi:power",
    "heat": "mdi:fire",
    "cool": "mdi:snowflake" ,
    "heat_cool": "mdi:sun-snowflake-variant" ,
    "dry": "mdi:heat-wave" ,
    "fan_only": "mdi:fan" ,
    "auto": "mdi:thermostat-auto"
}
"Default icons for the possible HVAC modes"