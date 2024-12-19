"The device class for the emulator"

import asyncio
import logging
import typing
from typing import *
import random as rnd
import json

from pathlib import Path
from math import ceil
from contextlib import suppress

import tkthread
import tkinter as tk

from PIL import Image, ImageTk

from inkBoarddesigner.platforms.desktop import device
from inkBoard.platforms.basedevice import InkboardDeviceFeatures, FEATURES

from PythonScreenStackManager.devices import PSSMdevice, windowed
from PythonScreenStackManager.tools import DummyTask, TouchEvent
from PythonScreenStackManager import constants as pssmconst

from . import const, pssm_functions

from ..tkinter import window
from ..tkinter.windows import DesignerWindow
from ..tkinter.widgets import PSSMCanvas
from .. import const as des_const

if TYPE_CHECKING:
    from inkBoard import config

_LOGGER = logging.getLogger(__name__)

# from inkBoard.platforms.basedevice import BaseDevice
##Cannot import the device yet -> it messes up the import of pssm
##But, can it not simply be imported later by inkBoard itself?

##Have platforms keep a emulate.json file.
##Holds default values like height and screen type
##Give key for config_features
##Models give keys for stuff

time_hint = Union[int,float,str]

test_init = {
    "required": {
        "model": {"type_hint": 'str'},
        "input": {},
        "stop_time": {"type_hint": str(time_hint)}
    },
    "optional": {

    }
}

def validate_platform_config(emulator_config: dict, config: "config"):
    """Validates the device entry in a config file against the requested platform.

    Parameters
    ----------
    emulator_config : Path
        Configuration settings for the emulator
    config : config
        The config to check

    Raises
    ------
    AssertionError
        Raised when a check fails. Either when the config contains superfluous arguments (aside from platform and name, which are filtered out), or an argument's value does not match the provided type hint.
    """

    platform_conf = emulator_config

    if "__init__" not in platform_conf:
        _LOGGER.warning(f"Cannot validate device config, .json has no __init__ entry.")
        return

    init = platform_conf["__init__"]
    if not "required" in init and not "optional" in init:
        _LOGGER.error("Cannot validate device config, required and/or optional argument keys are not present")
        return

    device_conf = dict(config.device)
    platform_name = device_conf.pop("platform")
    device_conf.pop("name") ##name and platform will be standard. Any platform should accept the name parameter.

    err = False

    for entry in device_conf:
        if entry not in init["required"] and entry not in init["optional"]:
            _LOGGER.error(f"Device config entry {entry} is not a valid argument for platform {platform_name}")
            err = True

    for arg, arg_dict in init["required"].items():
        try:
            assert arg in device_conf, f"Device config is missing required entry {arg}"
            if "type_hint" in arg_dict:
                try:
                    t = eval(arg_dict["type_hint"])
                    if isinstance(t, (type,typing._UnionGenericAlias)):
                        if isinstance(t, typing._UnionGenericAlias):
                            t = t.__args__
                        assert isinstance(device_conf[arg],t), f"Device config entry {arg} is of incorrect type. Should be of type(s) {t}"
                    else:
                        raise NameError(f"{t} is not an instance of type")
                except (NameError, TypeError):
                    _LOGGER.warning(f"Cannot determine type of argument {arg} from string value {arg_dict['type_hint']}. Not validating")
        except (AssertionError, KeyError) as exce:
            _LOGGER.error(exce.args[0], exc_info=None)
            err = True

    for arg, arg_dict in init["optional"].items():
        if arg not in device_conf:
            continue
        try:
            if "type_hint" in arg_dict:
                try:
                    t = eval(arg_dict["type_hint"])
                    if isinstance(t, (type,typing._UnionGenericAlias)):
                        if isinstance(t, typing._UnionGenericAlias):
                            t = t.__args__
                        assert isinstance(device_conf[arg],t), f"Device config entry {arg} is of incorrect type. Should be of type {t}"
                    else:
                        raise NameError(f"{t} is not an instance of type or a union")
                except (NameError, TypeError):
                    _LOGGER.warning(f"Cannot determine type of argument {arg} from string value {arg_dict['type_hint']}")
        except (AssertionError, KeyError) as exce:
            _LOGGER.error(exce.args[0], exc_info=None)
            err = True
    
    assert not err, "Device config failed validation. See logs for more info"
    return

class Device(device.Device):

    def __init__(self, config: "config"):
        
        emulated_platform: str = config.device["platform"]

        if "/" in emulated_platform or "\\" in emulated_platform:
            platform_folder = Path(emulated_platform)
        else:
            platform_folder = const.PLATFORM_FOLDER / emulated_platform

        assert platform_folder.exists(), f"Platform {emulated_platform} does not exist or is not installed"

        self.__emulated_platform = emulated_platform
        self.__emulated_platform_folder = platform_folder

        self._long_click_time = 0.5
        self._bound: set[tuple[tk.Widget, str["sequence"], str["function_id"]]] = set()

        self._emulated_platform = emulated_platform

        if "model" in config.device:
            model = config.device["model"]
        else:
            model = f"{emulated_platform.title()} Device"

        self._model = f"Emulated {model}"

        name = config.device.get("name", None)
        if not name: name = "inkBoard Emulator"

        self.window.title(f"inkBoard Designer - {self._model}")

        emulator_conf = {}
        if (platform_folder / "emulator.json").exists():
            with open(platform_folder / "emulator.json") as f:
                emulator_conf = json.load(f)

        if emulated_platform != "emulator" and config.designer.platform_validation:
            if emulator_conf:
                validate_platform_config(emulator_conf, config)
            else:
                _LOGGER.warning(f"Cannot validate config for platform {emulated_platform}, no emulator.json file")

        self._canvasLock = asyncio.Lock()

        ##These should be checked and be settable by reading out the config
        
        device_map = const.DEFAULT_DEVICE_SCHEMA.copy()
        device_map.update(emulator_conf)

        self._device_map = device_map

        if "width" in config.device:    ##The validation part should take care of width being illegal for a platform
            width = config.device["width"]
        elif device_map["width"] != None:
            width = device_map["width"]
        else:
            width = self.canvas.winfo_width()

        if "height" in config.device:    ##The validation part should take care of width being illegal for a platform
            height = config.device["height"]
        elif device_map["height"] != None:
            height = device_map["height"]
        else:
            height = self.canvas.winfo_height()

        features = InkboardDeviceFeatures(**device_map["features"])

        self.refresh_rate = device_map["refresh_rate"]

        if "screen_mode" in device_map:
            screenMode = device_map["screenmode"]
        elif "screen_type" in device_map:
            screentype = device_map["screen_type"]
            self._screenType = screentype
            if screentype in const.SCREEN_TYPES:
                screenMode = const.SCREEN_TYPES[screentype]
            else:
                screenMode = const.SCREEN_TYPES["default"]

        imgMode = device_map.get("img_mode", f"{screenMode}A")

        defaultColor = device_map.get("defaultColor",None)#"white")

        #Cannot use BaseDevice for this, since that would actually call the wrong super() when initialising
        PSSMdevice.__init__(self,features,
                            width,height,width,height,
                            screenMode, imgMode, defaultColor, name = name)

        if self.has_feature(FEATURES.FEATURE_BATTERY):
            self._battery = Battery(self)
        
        if self.has_feature(FEATURES.FEATURE_BACKLIGHT):
            self._backlight = Backlight(self)

        if self.has_feature(FEATURES.FEATURE_NETWORK):
            self._network = windowed.Network(self)

        self.canvas.set_size(width, height)

        self._canvasWidth = width
        self._canvasHeight = height

        self._windowWidth = self.window.winfo_width()
        self._windowHeight = self.window.winfo_height()

        self._screenImage = Image.new(screenMode,(self.screenWidth,self.screenHeight),
                                    None)
        self.last_printed_PIL = self._screenImage.copy()
        ImageTk.PhotoImage(self.last_printed_PIL)
        self._canvasImageTk = self.window.call_in_main_thread(
                ImageTk.PhotoImage, self.last_printed_PIL)
        
        self._canvasImageTag = None
        self.setup_emulator(config)        
        return
    
    #region
    @property
    def emulated_platform(self) -> str:
        "The platform currently being emulated"
        return self.__emulated_platform
    
    @property
    def emulated_platform_folder(self) -> Path:
        "The path to the actual platform's module"
        return self.__emulated_platform_folder

    @property
    def window(self) -> DesignerWindow:
        "The full designer window"
        return window

    @property
    def canvas(self) -> PSSMCanvas:
        "The tkinter canvas widget that displays the PSSM screen image."
        return window.screenCanvas

    @property
    def screenImage(self) -> Image.Image:
        "The actual image pictured on the screen, as gotten from PSSM. (I.e. the stack)"
        ##Check if this one is actually used in the windowed version
        ##Yes it is, for keeping the screen image, without any alterations from the printTK function
        return self._screenImage
    
    @property
    def screenWidth(self) -> int:
        "Width of the screen"
        return self._canvasWidth
    
    @property
    def viewWidth(self) -> int:
        return self.screenWidth

    @property
    def screenHeight(self) -> int:
        "Height of the screen"
        return self._canvasHeight
    
    @property
    def viewHeight(self) -> int:
        "Height of the screen"
        return self.screenHeight
    #endregion

    def setup_emulator(self, config): 
        ##Meant to setup a session to rougly emulate the platform that inkBoard will run on
        ##The emulator will setup most things itself via the device manifest, however an additional function will be made/checked for to set up additional stuff.
        ##However in that case do not forget to somehow clear those when reloading the config
        
        
        if self.has_feature(FEATURES.FEATURE_INTERACTIVE):
            
            if self.has_feature(FEATURES.FEATURE_PRESS_RELEASE):
                bind_func = self.canvas_event
            else:
                bind_func = self.simple_canvas_event

            funcid = self.canvas.bind("<Button-1>", bind_func)
            self._bound.add((self.canvas, "<Button-1>", funcid))

            funcid = self.canvas.bind("<ButtonRelease-1>", bind_func)
            self._bound.add((self.canvas,"<ButtonRelease-1>", funcid))

        if self.has_feature(FEATURES.FEATURE_RESIZE):
            self._resizeTask = DummyTask()
            funcid = self.window.bind("<Configure>", self._window_configure, add="+")
            self._bound.add((self.window, "<Configure>", funcid))
            if self.window.wm_resizable(None,None) != (True, True):
                self.window.resizable(True, True) ##Doing this reopens the mainwindow, so only doing it if required.
        else:
            if self.window.wm_resizable(None,None) != (False, False):
                self.window.resizable(False, False)

        if self.has_feature(FEATURES.FEATURE_BACKLIGHT):
            self.backlight.set_tkinter_settings()
        return

    def _quit(self):
        for widget, seq, funcid in self._bound:
            try:
                widget.unbind(seq,funcid)
            except tk.TclError:
                continue
        return

    async def _update_canvas(self, img: Image.Image = None):
        """Called by the base windowed device print_pil to update the canvas. Asyncio Lock is implemented to emulate device frame rates."""
        img = img.copy()
        async with self._canvasLock:
            await asyncio.sleep(1/self.refresh_rate)
            tkthread.call_nosync(self.__print_on_canvas, img)
        return

    def __print_on_canvas(self, img):
        self._canvasImageTk = ImageTk.PhotoImage(img)
        if self._canvasImageTag:
            self.canvas.itemconfig(self._canvasImageTag, image = self._canvasImageTk)
        else:
            self._canvasImageTag = self.canvas.create_image(0,0, anchor=tk.NW, image=self._canvasImageTk,
                                    tag=des_const.SCREEN_TAG) 
        self.canvas.update()

    def simple_canvas_event(self, event: tk.Event):
        self._lastEvent = event
        self._interactEvent.set()

    async def simple_canvas_event_handler(self):
        while self.Screen.printing:
            with suppress(asyncio.CancelledError):
                await self._interactEvent.wait()
                self._interactEvent.clear()

                try:
                    await asyncio.wait_for(self._interactEvent.wait(),
                            timeout=self._long_click_time)
                except asyncio.TimeoutError:
                    t = pssmconst.TOUCH_LONG
                    await self._interactEvent.wait()
                else:
                    t = pssmconst.TOUCH_TAP

                self._interactEvent.clear()
                x, y = (self._lastEvent.x, self._lastEvent.y)
                _LOGGER.verbose(f"Passing touch at {(x,y)} as {t}")
                await self.eventQueue.put(TouchEvent(x,y,t))


    async def event_bindings(self, eventQueue = None, grabInput=False):
        pssm_functions.build_element_tree(self.Screen)

        if self.has_feature(FEATURES.FEATURE_INTERACTIVE):
            self._eventQueue = eventQueue
            self._interactEvent = asyncio.Event(loop=self.Screen.mainLoop)
            self.Screen.mainLoop.create_task(self.simple_canvas_event_handler())
        
        self._updateWindowTask = asyncio.create_task(self._update_canvas_loop())

    async def _update_canvas_loop(self):

        while True:
            try:
                await asyncio.sleep(1/des_const.REFRESH_RATE)

            except asyncio.CancelledError:
                return

    async def _resize_window(self, event : Union[tk.Event,asyncio.Event]):
        ##Called when the window has been resized

        if event == None:
            pass

        elif isinstance(event,asyncio.Event):
            _, pending = await asyncio.wait([event.wait()],
                                            timeout=0.25)
            if pending:
                event.set()
            self.window.unbind("<ButtonRelease-1>")
        else:
            return
        
        self._windowWidth = self.window.winfo_width()
        self._windowHeight = self.window.winfo_height()

        self._canvasWidth = self._windowWidth - des_const.INTERFACE_WIDTH
        self._canvasHeight = self._windowHeight

        await self.parentPSSMScreen._screen_resized()

        self._screenImage = Image.new(self.screenMode,(self.screenWidth,self.screenHeight),None)
        self.last_printed_PIL = self._screenImage.copy()

        self.canvas["width"] = self.screenWidth
        self.canvas["height"] = self.screenHeight

        if self.has_feature(FEATURES.FEATURE_BACKLIGHT):
            self.backlight.size = (self.screenWidth,self.screenHeight)
            self.backlight._backlightImg = Image.new("RGBA", color=(0,0,0,0), size=(self.screenWidth,self.screenHeight))

        ##Maybe unlock the lock rn? Or forcibly print it -> do that.
        await self.parentPSSMScreen.print_stack()
        tkthread.call_nosync(self.__print_on_canvas, self.last_printed_PIL.copy())
        return

class Battery(device.BaseBattery):
    
    randomise = True

    def __init__(self, device):
        
        self._randomise = True

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
        return self.update_battery_state()
    
    def update_battery_state(self):

        if self._randomise:
            self._batteryCharge = rnd.randint(0,100)
            _LOGGER.verbose(f"Emulator has no battery, returning randomised value {self._batteryCharge}%")
            if self._batteryCharge == 100:
                self._batteryState = "full"
            else:
                self._batteryState = rnd.choice(["charging","discharging"])
        else:
            _LOGGER.verbose("Emulator has no battery, not updating")
        return (self._batteryCharge, self._batteryState)
    
    def _set_state(self, value :Literal["full","charging","discharging"]):
        "Manually set the battery state (overwritten when randomise is on and update_state is called)"
        self._batteryState = value

    def _set_charge(self, value : int):
        "Manually set the battery state (overwritten when randomise is on and update_state is called)"
        self._batteryCharge = value

class Backlight(windowed.Backlight):
    "Emulator backlight. Does nothing (may test with putting a dark shaded rectangle over the screen though)"
    def __init__(self, device):
        super().__init__(device)
        self._level = 0
        self.simulate = False
        self.__maxAlpha = 175
        

    @property
    def backlightImage(self) -> Image.Image:
        "The image to simulate the backlight with. Always returns a copy."
        return self._backlightImg.copy()

    def set_tkinter_settings(self, state=False):
        "Sets objects etc. so the backlight can be simulated in the emulator"
        self.screenCanvas = window.screenCanvas
        self.simulate = state
        self.size = (self._device.screenWidth, self._device.screenHeight)
        self.bgRect = False
        self.toggle_simulate(state=state)
        ##Probably do not need to do anything with the hiding/showing here, that can be done in the settings trace.

    def toggle_simulate(self, state : bool = None):
        "Toggles whether the backlight overlay is shown."
        if state == None:
            self.simulate = not self.simulate
        else:
            self.simulate = state
        _LOGGER.debug("Changing backlight")
        
        if self.simulate:
            _LOGGER.debug(f"Toggling backlight simulate. Brt is {self.brightness}")
            alpha = int(self.__maxAlpha - self.__maxAlpha*(self.brightness/100))
            self._backlightImg = Image.new("RGBA", color=(0,0,0,0), size=(self.size[0],self.size[1]))
            blImg = self.backlightImage
            blImg.putalpha(alpha) 
            self.blTk = ImageTk.PhotoImage(blImg)
            self.bgRect = self.screenCanvas.create_image(0,0, anchor=tk.NW, image=self.blTk)
        else:
            if self.bgRect: self.screenCanvas.delete(self.bgRect)

    async def __set_backlight_level(self, level):
        """
        Args:
            level (int): A frontlight level between 0 (off) and 100 (maximum)
        """
        if level < 0 or level > 100:
            return
        
        if not self.simulate:
            return
        
        if level == self._level:
            return
        
        alpha = int(self.__maxAlpha - self.__maxAlpha*(level/100))
        _LOGGER.verbose(f"Backlight brightness to {level}%; Alpha channel is {alpha}")
        blImg = self.backlightImage
        blImg.putalpha(alpha) 
        blTk = ImageTk.PhotoImage(blImg)

        if self.bgRect: 
            self.screenCanvas.itemconfig(self.bgRect, image = blTk)
        else:
            self.bgRect = self.screenCanvas.create_image(0,0, anchor=tk.NW, image=blTk)
        
        self.blTk = blTk
        self._level = level

    async def __transition(self,brightness : int, transition: float):
        if not self.transitionTask.done():
            self.transitionTask.cancel("New transition received")

        self.transitionTask = asyncio.create_task( self.__async_transition(brightness, transition))
        try:
            await self.transitionTask #@IgnoreException
        except asyncio.CancelledError as exce:
            _LOGGER.debug(f"Transition task to {brightness}% in {transition} seconds was cancelled")
        if self._device.parentPSSMScreen.printing:
            async with self._updateCondition:
                self._updateCondition.notify_all()

    async def __async_transition(self, brightness : int, transition: float):
        """
        Async function to provide support for transitions. Does NOT perform sanity checks

        Parameters
        ----------
        brightness : int
            the desired end brightness
        transition : float
            the transition time in seconds
        """
                    
        if transition == 0:
            await self.__set_backlight_level(brightness)
            return

        if self.brightness == brightness:
            return

        min_wait = 0.05
        wait = transition/(abs(self.brightness-brightness))
        step = -1 if self.brightness > brightness else 1

        async with self._lightLock:
            if wait < min_wait: 
                steps = ceil(transition/min_wait)
                for i in range(0,steps):
                    step = int(brightness - self.brightness)/(steps-i)
                    L = asyncio.gather(self.__set_backlight_level(self.brightness + step), 
                                    asyncio.sleep(min_wait))
                    await L #@IgnoreException
                await self.__set_backlight_level(brightness)
            else:
                while self.brightness != brightness:
                    L = asyncio.gather(self.__set_backlight_level(self.brightness + step), asyncio.sleep(wait))
                    await L #@IgnoreException

    async def turn_on_async(self, brightness : int = None, transition: float = None):
        """Async function to provide support for transitions at turn on. Does NOT perform sanity checks"""
        if self.simulate:
            _LOGGER.debug(f"Async turning on in {transition} seconds")
        
        if brightness == None:
            brightness = self.defaultBrightness
        
        if transition == None:
            transition = self.defaultTransition

        if self.brightness == brightness:
            ##Do nothing if the light is already at the correct level
            return

        await self.__transition(brightness,transition)

    def turn_on(self, brightness : int = None, transition : float = None):
        """Turn on the backlight to the set level"""

        if transition == None:
            transition = self.defaultTransition

        if brightness == None:
            brightness = self.defaultBrightness
        
        if transition < 0:
            _LOGGER.error("Transition time cannot be negative.")
            return
        
        if brightness < 0 or brightness > 100:
            _LOGGER.error(f"Brightness must be between 0 and 100. {brightness} is an invalid value")
            return
        
        asyncio.create_task(self.turn_on_async(brightness, transition))

    async def turn_off_async(self, transition: float = None):
        """Async function to provide support for transitions at turn off. Does NOT perform sanity checks"""
        _LOGGER.debug("Async turning off")
        if not self.state:
            ##Do nothing if the light is already off
            return

        if transition == None:
            transition = self.defaultTransition

        await self.__transition(0,transition)

    def turn_off(self, transition : float = None):
        """Turns off the backlight to the set level"""
        if not self.state:
            ##Backlight is already off, no need to do anything
            return

        if transition == None:
            transition = self.defaultTransition

        if transition < 0:
            _LOGGER.error("Transition time cannot be negative.")
            return

        asyncio.create_task(self.turn_off_async(transition))

    def toggle(self, brightness : int = None, transition : float = None):
        if self.state:
            self.turn_off(transition)
        else:
            self.turn_on(brightness,transition)

    async def toggle_async(self, brightness: int = None, transition: float = None):
        if self.state:
            await self.turn_off_async(transition)
        else:
            await self.turn_on_async(brightness,transition)
