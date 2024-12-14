
from pathlib import Path

from inkBoard.constants import INKBOARD_FOLDER
from inkBoard.platforms.basedevice import FEATURES

DEFAULT_DEVICE_SCHEMA = {
    "screen_type": "LED",
    "width": None,
    "height": None,
    "refresh_rate": 20,
    "features": {
        FEATURES.FEATURE_NETWORK: True,
        FEATURES.FEATURE_INTERACTIVE: True,
        FEATURES.FEATURE_ROTATION: False,
        FEATURES.FEATURE_RESIZE: True,
        FEATURES.FEATURE_BATTERY: True,
        FEATURES.FEATURE_BACKLIGHT: True,
        FEATURES.FEATURE_PRESS_RELEASE: True,
        FEATURES.FEATURE_POWER: False
    }
}

SCREEN_TYPES = {
    "default": "RGB",
    "e-ink": "L"
}

PLATFORM_FOLDER = Path(__file__).parent.parent / "platforms"
"Folder holding the available platforms."