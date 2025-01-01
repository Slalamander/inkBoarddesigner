"Integration to run inkBoard desktop in a system tray"

from typing import *

import inkBoard

if TYPE_CHECKING:
    from inkBoard import config, core as CORE
    from .trayicon import TrayIcon

_LOGGER = inkBoard.getLogger(__name__)

async def async_setup(core: "CORE", config: "config"):

    if config.device["platform"] != "desktop":
        _LOGGER.error("Using the systemtray integration requires the desktop platform")
        return False

    from .trayicon import TrayIcon
    icon = TrayIcon(core, config.inkBoard.name)
    
    return icon

async def async_start(core: "CORE", trayicon: "TrayIcon"):
    trayicon.run_detached()
    return