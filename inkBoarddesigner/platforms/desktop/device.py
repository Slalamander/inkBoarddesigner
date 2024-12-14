"""
This device can be used in desktop environments.
It is an extension of the base device that comes with PythonScreenStackManager, since it (will) provide functionality for somewhat easy extension of the functionality using integrations.
"""

import __main__
import asyncio
import tkinter as tk
from typing import TYPE_CHECKING, Union
from pathlib import Path
import platform

from PIL import Image, ImageTk

from inkBoard.platforms.basedevice import BaseDevice, InkboardDeviceFeatures, FEATURES,\
                                    BaseBacklight, BaseBattery, BaseNetwork
from inkBoard.constants import INKBOARD_FOLDER

from PythonScreenStackManager.devices import windowed
from PythonScreenStackManager.tools import DummyTask

try:
    #plyer module is optional, provides additional device features
    import plyer #@IgnoreExceptions
except ModuleNotFoundError:
    plyer = False

if TYPE_CHECKING:
    from PythonScreenStackManager.pssm_types import *

class Device(BaseDevice, windowed.Device):
    """inkBoard device for desktop environments

    This device can be used on any OS platform where python's tkinter library can be used for application windows.
    Some optional features exist, but it can be used without any additional libraries.

    Parameters
    ----------
    name : str, optional
        The name of the device, also used to name the window, by default None
    frame_rate : int, optional
        The amount of times the window is updated per second, by default 20.
        Since this is a dashboarding interface, the value does not need to be very high to still have a decent running experience.
        The main performance bottleneck probably lies in the generating of elements and the fact that it is run in Python.
    width : int, optional
        The initial width of the window, by default 1280
    height : int, optional
        The initial height of the window, by default 720
    fullscreen : bool, optional
        Whether to start the window in fullscreen, by default False
        screenWidth and screenHeight are set to the correct value if this True.
        The device provides a shorthand function for toggling fullscreen, and binds the F11 key to toggle it as well.
    resizeable : bool, optional
        Allows the window to be resized by dragging the edges, by default False
    cursor : str, optional
        The type of cursor to use when the mouse is on the dashboard. By default "target"
        see https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/cursors.html for available types.
    color_mode : str, optional
        The image mode to print the final screen image in, by default "RGB". Use "L" or "LA" if you'd want black and white.
    default_color : ColorType, optional
        The default color (i.e. assumed background color) of the device, by default "white"
    interactive : bool, optional
        Whether the dashboard can be interacted with, by default True
    network : bool, optional
        Whether to use network_features, by default False
        This indicates the device can access the internet and periodically pols the network properties. Setting it to False does not actually block off internet access to the programme.
    backlight : bool, optional
        Whether to simulate screen brightness, i.e. print a transparent black rectangle over the dashboard, by default False. May affect performance when used.
    backlight_alpha : int, optional
        The maximum allowed alpha value of the backlight rectangle, so the transparancy when the backlight is considered off. by default 175
        0 is the minimum value, which is the same as not using the backlight feature. 255 is the maximum value, which means the rectangle is not transparant at all when it is off.
    window_icon : str, Path
        The icon for the window. This must be a .ico file
        Also, on windows, due to how applications are managed, inkBoard will not use this icon in the taskbar.
        Defaults to the 'inkBoard', which means it uses the inkBoard logo icon.
    """  

    def __init__(self, name : str = None,
                frame_rate : int = 20, width = 1280, height = 720, fullscreen : bool = False, resizeable : bool = False, cursor : str = "target",
                color_mode : str = "RGB",  default_color: "ColorType"  = "white",
                interactive : bool = True, network : bool = True, backlight : bool = False, backlight_alpha : int = 175,
                window_icon: Union[str,Path] = "inkboard",
                ):

        self._model = None

        feature_dict = {FEATURES.FEATURE_INTERACTIVE: interactive, FEATURES.FEATURE_PRESS_RELEASE: interactive,
                        FEATURES.FEATURE_BACKLIGHT: backlight, FEATURES.FEATURE_NETWORK: network,}
        if plyer:
            bat_state = plyer.battery.get_state()
            if not all(v is None for v in bat_state.values()):
                feature_dict[FEATURES.FEATURE_BATTERY] = True

        features = InkboardDeviceFeatures(**feature_dict)

        if backlight:
            self._backlight = windowed.Backlight(self, backlight_alpha)

        ##Gotta see what needs to be overwritten after this
        windowed.Device.__init__(self, name, frame_rate,  
                        width, height, fullscreen, resizeable,
                        cursor, color_mode, "RGBA", default_color, features=features)
        
        if window_icon in {None, "inkboard"}:
            window_icon = Path(INKBOARD_FOLDER) / "files" / "icons" / "inkboard.ico"
        self.window.wm_iconbitmap(window_icon)

        if name == None:
            self.window.title(f"inkBoard")
        else:
            self.window.title(self.name)

class Battery(BaseBattery):
        "Device battery. Not used if unsupported by plyer."

        def __init__(self, device):
            
            charge, state = self.update_battery_state()

            super().__init__(device, charge, state)

        async def async_update_battery_state(self)-> tuple[int,str]:
            """
            Update the battery state. Returns the result.

            Returns
            -------
            tuple[int,str]
                Tuple with [charge percentage, state]
            """
            ##idk if this is blocking, if so, needs to go to a thread
            self.update_battery_state()
        
        def update_battery_state(self):
            state = plyer.battery.get_state()
            charge_perc = state.get("percentage", 0)

            if state["isCharging"]:
                charge_state = "charging"
            else:
                charge_state = "discharging" if charge_perc < 100 else "full"

            t = (charge_perc, charge_state)
            self._update_properties(t)
            return t
    #endregion

