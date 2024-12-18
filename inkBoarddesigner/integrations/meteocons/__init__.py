"""Provides meteocons by Bas Milius for inkBoard. Not all icons are included in order to keep the file size down.
Not all icons are included. This integration is meant to be used by other integrations, and has no configuration to go along with it. 
To include it in a package, add meteocons: to your config.
"""

from typing import Literal
from pathlib import Path

import inkBoard

_LOGGER = inkBoard.getLogger(__name__)

def parse_weather_icon(condition: str, nighttime: bool = False, icon_type: Literal["filled","outline"] = "filled") -> Path:
    """Parses the appropriate meteocon icon for the provided condition

    Parameters
    ----------
    condition : str
        The weather condition to get the icon of
    nighttime : bool, optional
        Whether to look for for the nighttime version of the condition, by default False
        If the nighttime icon does not exist, returns the daytime version
    icon_type : Literal[&quot;filled&quot;,&quot;outline&quot;], optional
        The type of icon to return, by default "filled"

    Returns
    -------
    Path
        The path to the icon's file
    """    
    if condition in {"default", None}:
        icon_id = METEOCONS_WEATHER_ICONS["default"]

    elif nighttime:
        icon_id = METEOCONS_WEATHER_ICONS["night"].get(condition,METEOCONS_WEATHER_ICONS["day"].get(condition,"default"))
    else:
        icon_id = METEOCONS_WEATHER_ICONS["day"].get(condition,"default")

    if icon_id == "default":
        _LOGGER.warning(f"Could not find weather condition {condition} in the condition day keys, returning default value")
        icon_id = METEOCONS_WEATHER_ICONS["default"]

    icon_file = f"{icon_id}{IMAGE_FILE_TYPE}"
    if icon_type == "outline":
        return METEOCONS_PATH_OUTLINE / icon_file
    else:
        return METEOCONS_PATH_OUTLINE / icon_file
    
def parse_icon(icon: str, icon_type: Literal["filled","outline"] = "filled") -> Path:
    """Parses the path to a meteocon icon

    Parameters
    ----------
    icon : str
        The icon to parse
    icon_type : Literal[&quot;filled&quot;,&quot;outline&quot;], optional
        The type of icon to parse, by default "filled"

    Returns
    -------
    Path
        The path to the icon, or None if it was not found
    """

    if not "." in icon:
        icon_file = f"{icon}{IMAGE_FILE_TYPE}"
    else:
        icon_file = icon

    if icon_type == "outline":
        p = METEOCONS_PATH_OUTLINE / icon_file
    else:
        p = METEOCONS_PATH_OUTLINE / icon_file
    
    if not p.exists():
        _LOGGER.error(f"Meteocon icon {icon_file} does not exist")
        return
    
    return p

def setup(core, config):
    return True

METEOCONS_PATH_OUTLINE = Path(__file__).parent / "icons/meteocons/outline"
METEOCONS_PATH = Path(__file__).parent / "icons/meteocons/filled"

IMAGE_FILE_TYPE = ".png"
##File type of the included meteocons

METEOCONS_WEATHER_ICONS : dict = {"default": "cloudy",
        "day": {
            "clear-night": "clear-night",
            'cloudy':"overcast",
            "exceptional": "rainbow",
            'fog': "fog",
            'hail': "hail",
            'lightning': 'thunderstorms-extreme',
            "lightning-rainy": "thunderstorms-extreme-rain",
            "partlycloudy": "partly-cloudy-day",
            "pouring": "extreme-rain",
            'rainy': "overcast-drizzle",
            "snowy": "overcast-snow",
            "snowy-rainy": "overcast-sleet",
            "sunny": "clear-day",
            "windy": "umbrella-wind",
            "windy-variant": "umbrella-wind-alt",

            "hazy": "haze",
            "hurricane": "hurricane",
            "dust": "dust",
            "partly-lightning": "thunderstorms-day-overcast",
            "partly-rainy": "overcast-day-drizzle",
            "partly-snowy": "overcast-day-snow",
            "partly-snowy-rainy": "overcast-day-sleet",             
            "snowy-heavy": "extreme-snow",
            "tornado": "tornado"
            },
        "night": {
            "clear-night": "falling-stars",
            'cloudy':"overcast-night",
            "exceptional": "rainbow",
            'fog': "fog-night",
            'hail': "partly-cloudy-night-hail",
            'lightning': 'thunderstorms-night-extreme',
            "lightning-rainy": "thunderstorms-night-extreme-rain",
            "partlycloudy": "overcast-night",
            "pouring": "extreme-night-rain",
            'rainy': "overcast-night-drizzle",
            "snowy": "overcast-night-snow",
            "snowy-rainy": "overcast-night-sleet",
            "sunny": "falling-stars",

            "hazy": "overcast-night-haze",
            "dust": "dust-night",
            "partly-lightning": "thunderstorms-night-overcast",
            "partly-rainy": "partly-cloudy-night-drizzle",
            "partly-snowy": "partly-cloudy-night-snow",
            "partly-snowy-rainy": "partly-cloudy-night-sleet",             
            "snowy-heavy": "extreme-night-snow",
            }}
"Dict linking meteocon images to conditions. Suitable for both filled and outlined. Does not yet have the .png extension."

METEOCONS_FORECAST_ICONS : dict = {
                        "datetime" : None,
                        "cloud_coverage": "cloud-up",
                        "humidity": "humidity",
                        "apparent_temperature": "thermometer-sunny",
                        "dew_point": "thermometer-raindrop",
                        "precipitation": "raindrop-measurement",
                        "pressure": "barometer",
                        "temperature": "thermometer",
                        "templow": "thermometer-colder",
                        "wind_gust_speed": "wind-alert",
                        "wind_speed": "wind",
                        "precipitation_probability": "raindrop",
                        "uv_index": "uv-index",
                        "wind_bearing": "windsock"
                            }
"Meteocon icons for forecast entries."