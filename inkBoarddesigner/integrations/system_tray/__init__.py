"Integration to run inkBoard desktop in a system tray"

from typing import *

import inkBoard

if TYPE_CHECKING:
    from inkBoard import config, core as CORE
    from .trayicon import TrayIcon

_LOGGER = inkBoard.getLogger(__name__)
TRAYSIZE = 50   #Traysize in pixel
TOLERANCE = 1.1 #Small tolerance multiplier to enlarge the identification of clicks on the tray correctly

async def async_setup(core: "CORE", config: "config"):

    if config.device["platform"] != "desktop":
        _LOGGER.error("Using the systemtray integration requires the desktop platform")
        return False

    from .trayicon import TrayIcon
    icon = TrayIcon(core, config)
    
    return icon

async def async_start(core: "CORE", trayicon: "TrayIcon"):
    trayicon.start()
    return

def stop(core: "CORE", trayicon: "TrayIcon"):
    trayicon.stop()
    return

class system_tray_entry(TypedDict):

    icon: Union[str,Literal["circle","droplet"]] = "circle"
    "The icon to show in the taskbar."

    hide_window: bool = False
    "Hides the window from the taskbar when it is minimised"

    toolwindow: bool = False
    """Turns inkBoard into a toolwindow

    The hides the window from the taskbar entirely, and removes the borders from the window. It also starts inkBoard minimised.
    This means the window cannot be resized or moved manually.
    Size can be set in the device config. The integration will take care of positioning the window around the icon. Optionally use the tray_size option to improve the alignment.
    """

    tray_size: int = TRAYSIZE
    "Size of the system tray, in pixels. Used when using the toolwindow option"
