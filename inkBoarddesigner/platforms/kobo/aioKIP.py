"""Asyncio implementation of KIP
KIP : Kobo Input Python
Taken from
https://github.com/shermp/go-kobo-input
and translated very roughly to Python by Mavireck
Rewritten for asyncio by Slalamander
"""

import asyncio
import os,sys
import struct
from time import time
from fcntl import ioctl
import logging
from contextlib import suppress

from typing import *

from .fbink import API as fbink
from . import grabInput as grabber

class EventPacket(NamedTuple):
    time_sec: int
    time_u_sec: int
    event_type: int
    event_code: int
    event_value: int

DEFAULT_INPUT_DEVICE = "/dev/input/event1"
FORMAT = 'llHHI'
EVENT_SIZE = struct.calcsize(FORMAT)

VERBOSE = int(logging.DEBUG/2)

_LOGGER = logging.getLogger(__name__)

##From testing: seems that press = 0 and release = 0 gives the correct results for both pressure and touch?
##For Glo: button takes precedent. Pressure only to be utilised for more complicated stuff
##Also, (my) thumbs seem to mess up touch detection as they probably move too easily.
##Touchscreen is an IR one anyways, so the pressure event should not be pressure?
BUTTON_PRESS = 0
BUTTON_RELEASE = 1

PRESSURE_PRESS = 0
PRESSURE_RELEASE = 1

TOUCH_PRESSED = "PRESSED"
TOUCH_RELEASED = "RELEASED"

TOUCH_SHORT = "SHORT-TOUCH"
TOUCH_LONG = "LONG-TOUCH"

DEFAULT_HOLD_TIME = 0.5
DEFAULT_DEBOUNCE_TIME = 0.01

time_sec = TypeVar("TimeSec", bound=int)
time_u_sec = TypeVar("TimeUsec", bound=int)
ev_type = TypeVar("EvenType", bound=int)
ev_code = TypeVar("EventCode", bound=int)
ev_value = TypeVar("EventValue", bound=int)

event_types = {
	"Sync": 0,
	"Key": 1,
	"Absolute": 3,
}

event_key_codes = {
    "Btn2": 258,
	"BtnX": 307,
	"BtnY": 308,
	"Touch": 330,
}

event_abs_codes = {
    "X": 0,
    "Y": 1,
    "Hat0X": 16,
    "Hat0Y": 17,
    "Pressure": 24,
    "unknowns": [48,50,53,54,57]    
    ##Not sure what 50 and 57 do, values do not seem to change either
    ##Some of the other have to with pressure it seems, according to the GO code
}

evSyn = event_types["Sync"]
evAbs = event_types["Absolute"]
evKey = event_types["Key"]
btnTouch = event_key_codes["Touch"]

synReport            = 0
synDropped           = 3
synMTreport          = 2
absMTposX            = 53
absMTposY            = 54
absMTPressure        = 58
absMTtouchWidthMajor = 48

absX = {event_abs_codes["X"], event_abs_codes["Hat0X"], absMTposX}
absY = {event_abs_codes["Y"], event_abs_codes["Hat0Y"], absMTposY}
absPressure = {absMTPressure, absMTtouchWidthMajor, event_abs_codes["Pressure"]}

##The order in which a complete touch event seems to be transmitted:
##First the button press event is emitted
##Until the touch is moved, no coordinates come in (Hence it is not possible to differentiate between press and release, only the time a touch takes)
##X and Y are emitted
##Button release event is emitted

##X and Y do update when moving the finger, but that also emites the button release event. 
##Pressure does not seem to really correlate with this.
##I.e. moving your finger still emits pressure as false, and does not register a touch
##And when removing your finger, events are emitted again, so having a timeout waiting for new x/y updates does not really work either.


class InputQueue(asyncio.Queue):
    """Subclass of Asyncio Queue that passes on touch events.

    Asyncio implementation of KIP (Kobo Input Python). Simply await `InputQueue.get()` to get the touch events as they come in.
    Currently only supports press and release events, which can be evaluated using the `TOUCH_PRESSED` and `TOUCH_RELEASED` constants of this package.
    The first touch is never dispatched since it only emits a release event, no coordinates.

    General usage advice: debounce can be relatively big, as the screen is very sensitive. For holding, use a small finger, since it does not register those as moving as easily.
    I got the most consistent results using a key (I did not have a stylus on hand), though the smaller the object, the more likely it is to not cross any of the IR beams.

    Parameters
    ----------
    debounce_time : float, optional
        The minimum time between the press and release event for a touch to be valid, by default DEFAULT_DEBOUNCE_TIME
    long_click_time : float, optional
        The minimum time needed to hold a press for it to be dispatched as a long click, by default DEFAULT_HOLD_TIME
    input_device : str, optional
        Path the file that functions as the touch input, by default DEFAULT_INPUT_DEVICE
    loop : asyncio.AbstractEventLoop, optional
        the loop to attach to, by default None
    """    

    def __init__(self, debounce_time: float = DEFAULT_DEBOUNCE_TIME, long_click_time: float = DEFAULT_HOLD_TIME, input_device: str = DEFAULT_INPUT_DEVICE, 
                loop: asyncio.AbstractEventLoop = None):

        super().__init__(loop=loop)
        self._packet_queue = asyncio.Queue(loop=loop)
        self.__full_touch_event = asyncio.Event(loop=loop)
        self.__full_touch_event.set()
        if loop == None:
            loop = asyncio.get_running_loop()
        # self._output_queue = output_queue

        self._debounce_time = debounce_time
        self._long_click_time = long_click_time

        self._fileobject = open(input_device, "rb")   
        loop.add_reader(self._fileobject, self._read_inputdevice_line)
        self._read_task = loop.create_task(self._read_touch_packet())
        ioctl(self._fileobject, grabber.EVIOCGRAB(1), True)
        

    def __del__(self):
        ioctl(self._fileobject, grabber.EVIOCGRAB(1), False)
        self._fileobject.close()
        print("Input device file closed")

    async def get(self) -> tuple[int,int,Union[TOUCH_PRESSED,TOUCH_RELEASED]]:
        return await super().get()

    def _read_inputdevice_line(self):
        line = self._fileobject.read(EVENT_SIZE)
        inp = struct.unpack(FORMAT, line)
        if not inp:
            _LOGGER.log(VERBOSE, f"binary read failed {inp}")
            print("binary read failed ", inp)
            return
        self._packet_queue.put_nowait(EventPacket(*inp))
        return
    
    async def _read_touch_packet(self):
        

        badPacket = False
        self.__eventdict = {}
        while not self._fileobject.closed:
            inp: EventPacket = await self._packet_queue.get()
            if inp.event_type == evSyn and inp.event_code == synDropped:
                badPacket = True
                continue
            if badPacket and inp.event_type == evSyn and inp.event_code == synReport:
                self.__eventdict = {}
                badPacket = False
                continue
            if not badPacket:
                self._decode_event(inp)
                await asyncio.sleep(0)
                if inp.event_type == evSyn and inp.event_code == synReport and not self.__full_touch_event.is_set():
                    asyncio.create_task(self._wait_for_event_dispatch())
        
    def _decode_packets(self, packets: list[EventPacket]):

        x, y = -1, -1
        touch = None
        pressure = None

        _LOGGER.log(5, f"Decoding {len(packets)} input event packets")
        for event in packets:
            if event.event_type == evKey: # and touch == None:
                #Some, but not all Kobo's report a BTN_TOUCH event
                #For the Glo HD I'm testing on, it doesn't even seem consistend
                if event.event_code == btnTouch and touch == None:
                    if event.event_value == BUTTON_PRESS:
                        touch = True
                    else:
                        touch = False
                    
                    print(f"Button touch set to {touch}")
            elif event.event_type == evAbs:
                if event.event_code in absX:
                    x = int(event.event_value)
                    print(f"X set to {x}")
                    
                elif event.event_code in absY:
                    y = int(event.event_value)
                    
                elif event.event_code in absPressure and pressure == None:
                    if event.event_value == PRESSURE_PRESS:
                        pressure = True
                    else:
                        pressure = False
                    print(f"Pressure set to {pressure}")

            # if x >= 0 and y >= 0 and touch != None and pressure != None:
            #     break
        
        if x < 0 or y < 0 or (touch == pressure == None):
            _LOGGER.log(VERBOSE, "Could not decode complete touch packet")
            return (x, y, TOUCH_RELEASED)

        if x >= 0 and y >= 0 and pressure != None:
            ##Kind of annoying, but there does not seem to be a release event when dragging.
            ##So probably pressure/sliding would need a seperate handler.
            pass

        ##Currently works, though it's rather finicky with slight movements causing a release

        if touch != None:
            touch_val = TOUCH_PRESSED if touch else TOUCH_RELEASED
        else:
            touch_val = None

        return (x, y, touch_val)

    def _decode_event(self, event: EventPacket):

        if event.event_type == evKey:
            #Some, but not all Kobo's report a BTN_TOUCH event
            #For the Glo HD I'm testing on, it doesn't even seem consistent
            if event.event_code == btnTouch:
                if event.event_value == BUTTON_PRESS:
                    self.__eventdict["touch-true"] = True
                    self.__full_touch_event.clear()
                else:
                    self.__eventdict["touch-false"] = False
                    self.__full_touch_event.set()
                
        elif event.event_type == evAbs and "touch-true" in self.__eventdict:
            if event.event_code in absX:
                x = int(event.event_value)
                self.__eventdict["x"] = x
            elif event.event_code in absY:
                y = int(event.event_value)
                self.__eventdict["y"] = y
            elif event.event_code in absPressure:
                if event.event_value == PRESSURE_PRESS:
                    pressure = True
                else:
                    pressure = False
                self.__eventdict["pressure"] = pressure

    def _is_complete_event(self) -> bool:
        return not bool({"x","y","touch-true", "touch-false"} - set(self.__eventdict.keys()))

    def _rotate_coordinates(self, x: int, y: int):
        "Rotates the x and y coordinates received such that the upper left corner registers as (0,0) and x is the horizontal axis and y is the vertical axis"

        ##canonical 0 is upright portrait, which will be considered the general starting point BUT device has 0 rota
        rota = fbink.current_rota
        rx = x
        ry = y
        if rota == 0:
            ##No need to transpose them
            rx = x
            ry = y
        elif rota == 1:
            rx = y
            ry = fbink.screen_height - x
        elif rota == 2:
            rx = fbink.screen_width - x
            ry = fbink.screen_height - y
        elif rota == 3:
            rx = fbink.screen_width - y
            ry = x

        _LOGGER.log(VERBOSE, f"Rotation of {rota} (Canonical: {fbink.current_rota_canonical}), Original (x,y): {(x,y)}, rotated to (rx,ry): {(rx, ry)}.")
        return (rx, ry)

    async def _wait_for_event_dispatch(self):
        ##When gathering a touch, waits for the touch release event
        ##Does not dispatch if it completes within debounce
        ##Then determines if it is a long click or a short click
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self.__full_touch_event.wait(),
                                timeout=self._debounce_time)
            _LOGGER.log(VERBOSE, "Debounced touch")
            return
        
        await asyncio.sleep(0)

        try:
            await asyncio.wait_for(self.__full_touch_event.wait(),
                    timeout=self._long_click_time)
        except asyncio.TimeoutError:
            t = TOUCH_LONG
            await self.__full_touch_event.wait()
        else:
            t = TOUCH_SHORT

        if not self._is_complete_event():
            return

        x = self.__eventdict["x"]
        y = self.__eventdict["y"]
        self.__eventdict = {}

        _LOGGER.log(VERBOSE, f"Passing touch at {(x,y)} as {t}")
        x,y = self._rotate_coordinates(x,y)
        await self.put((x,y,t))


