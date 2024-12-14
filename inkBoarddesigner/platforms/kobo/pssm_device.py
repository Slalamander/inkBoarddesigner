"""Kobo device for working with only PSSM (not inkBoard)
"""

#!/usr/bin/env python
import sys
import os
import socket
import asyncio
import logging
import concurrent.futures
from typing import *
from pathlib import Path
from math import ceil
from contextlib import suppress

#Fbink functions etc. can best be checked here: https://github.com/NiLuJe/FBInk/blob/master/fbink.h
#But this is all in C, so some translating may be needed -> yawk has an fbink mock

from PythonScreenStackManager import constants as const, devices as basedevice, tools
from PythonScreenStackManager.tools import DummyTask, TouchEvent
from PythonScreenStackManager.pssm_types import *

from PIL import Image, ImageFont, ImageOps

from . import aioKIP, util
from .aioKIP import InputQueue
from .fbink import API as FBInk

_LOGGER = logging.getLogger(__name__)

path_to_pssm_device = os.path.dirname(os.path.abspath(__file__))

touchPath 			= "/dev/input/event1"
batteryCapacityFile = "/sys/devices/platform/pmic_battery.1/power_supply/mc13892_bat/capacity"
batteryStatusFile   = "/sys/devices/platform/pmic_battery.1/power_supply/mc13892_bat/status"

original_truetype = ImageFont.truetype
def truetype_wrapper(font = None, size: int = 10, index: int = 0, encoding: str = "", layout_engine = None):
	"Wrapper for truetype fonts to accept Path instance as font value"
	if isinstance(font,Path):
		font = str(font)
	return original_truetype(font,size,index,encoding,layout_engine)

ImageFont.truetype = truetype_wrapper

def PIL_cover_wrapper(image: Image.Image, size: tuple[int, int], method: int = Image.BICUBIC):
	"Wrapper function for PIL cover, since it is not available on the fbink provided PIL"

	##this is literally taken from the source of PIL.
	im_ratio = image.width / image.height
	dest_ratio = size[0] / size[1]

	if im_ratio != dest_ratio:
		if im_ratio > dest_ratio:
			new_height = round(image.height / image.width * size[0])
			if new_height != size[1]:
				size = (size[0], new_height)
		else:
			new_width = round(image.width / image.height * size[1])
			if new_width != size[0]:
				size = (new_width, size[1])
	return image.resize(size, resample=method)

ImageOps.cover = PIL_cover_wrapper

class ResamplingWrapper:
	"Wrapper for the PIL resampling class to at least provide the necessary constants"
	NEAREST = Image.NEAREST
	BOX = Image.BOX
	BILINEAR = Image.BILINEAR
	HAMMING = Image.HAMMING
	BICUBIC = Image.BICUBIC
	LANCZOS = Image.LANCZOS

Image.Resampling = ResamplingWrapper


full_device_name = f"{FBInk.platform} {FBInk.device_name}"

class Device(basedevice.PSSMdevice):
	
	def __init__(self, name: str = full_device_name, kill_os: bool = True,
			touch_debounce_time: DurationType = aioKIP.DEFAULT_DEBOUNCE_TIME, hold_touch_time: DurationType = aioKIP.DEFAULT_HOLD_TIME, input_device_path: str = aioKIP.DEFAULT_INPUT_DEVICE):
		features = basedevice.DeviceFeatures(interactive=True, 
									battery=True, backlight=True, network=True)

		if kill_os:
			util.kill_os()

		self._battery = Battery()
		self._backlight = Backlight(self)
		self._network = Network()

		super().__init__(features, 
				FBInk.screen_width, FBInk.screen_height, FBInk.view_width, FBInk.view_height,
				"RGBA", "RGBA", "white",
				name)

		self.__KIPargs = {"input_device": input_device_path}
		self.__KIPargs["debounce_time"] = tools.parse_duration_string(touch_debounce_time)
		self.__KIPargs["long_click_time"] = tools.parse_duration_string(hold_touch_time)

	#region
	@property
	def deviceName(self) -> str:
		return full_device_name

	@property
	def screenWidth(self)-> int:
		"Width of the screen"
		return FBInk.screen_width

	@property
	def screenHeight(self)-> int:
		"Height of the screen"
		return FBInk.screen_height

	@property
	def viewWidth(self)-> int:
		"Viewable width of the screen (taking into account possible bezels e.g.)"
		return FBInk.view_width

	@property
	def viewHeight(self)-> int:
		"Viewable height of the screen (taking into account possible bezels e.g.)"
		return FBInk.view_height
	
	@property
	def rotation(self) -> RotationValues:
		i = FBInk.current_rota_canonical
		return get_args(RotationValues)[i]
	
	@property
	def battery(self) -> "Battery":
		return self._battery
	
	@property
	def backlight(self) -> "Backlight":
		return self._backlight
	
	@property
	def network(self) -> "Network":
		return self._network
	#endregion

	def print_pil(self, imgData, x, y, isInverted=False):
		_LOGGER.debug("Printing to device screen")
		if imgData.mode != self.screenMode:
			imgData = imgData.convert(self.screenMode)

		FBInk.fbink_print_pil(imgData,x,y)
		
	async def async_pol_features(self):
		await self.battery.async_update_battery_state()
		await self.network.async_update_network_properties()
		return

	async def event_bindings(self, touch_queue = None):
		self._eventQueue = InputQueue(**self.__KIPargs)
		with suppress(asyncio.CancelledError):
			while True:
				(x,y,action) = await self.eventQueue.get()
				if action == aioKIP.TOUCH_SHORT:
					touch_action = const.TOUCH_TAP
				else:
					touch_action = const.TOUCH_LONG

				await touch_queue.put(TouchEvent(x,y,touch_action))
		return

	def _quit(self):
		self.close_print_handler()

	@staticmethod
	def close_print_handler():
		FBInk.close()
		
	async def _rotate(self, rotation=None):
		if isinstance(rotation, str):
			rotation = get_args(RotationValues).index(rotation)
		await asyncio.to_thread(FBInk.rotate_screen(rotation))
		await self.Screen._screen_resized()
		await asyncio.to_thread(FBInk.screen_refresh())


	def clear_screen(self):
		"Clears the entire screen"
		FBInk.screen_clear()
	
	def refresh_screen(self, skip_clear: bool = False):
		"Refreshes the entire screen. By default clears it first"
		if not skip_clear:
			self.clear_screen()
		
		FBInk.screen_refresh()

	def set_waveform(self, mode):
		FBInk.set_waveform(mode)
	


# #################### - Hardware etc. - #############################################
class Backlight(basedevice.Backlight):
	'''
	The backlight of the device. Provides callbacks to the state, and functions to turn on, off, or toggle it. Upon initialising this class, the light will be set to 0 to ensure the level is correct
		defaultBrightness (int): default brightness to turn on the backlight too, if not brightness provided (between 1-100)
		defaultTransition (float): default time in seconds for the fade. For smooth fades, 0.5 seems to be the minimum value from my tests.
	'''
	def __init__(self, device: Device, defaultBrightness : int = 50, defaultTransition : float = 0):

		##Ensuring the backlight is off when the dashboard starts, so the brightness and state are correct
		self.__set_backlight_level(0)

		self.__transitionExecutor = concurrent.futures.ThreadPoolExecutor(1,thread_name_prefix="backlightthread")

		super().__init__(device, defaultBrightness, defaultTransition)

	#region
	@property
	def brightness(self) -> int:
		"""The brightness of the backlight (0 - 100)"""
		return self._level

	@property
	def state(self) -> bool:
		"""The state (on/off) of the backlight as a boolean (True/False)"""
		return True if self._level > 0 else False

	@property
	def defaultBrightness(self) -> int:
		"""The default brightness to turn the backlight on to"""
		return self._defaultBrightness

	@defaultBrightness.setter
	def defaultBrightness(self, value : int):
		if value >= 0 and value <= 100:
			self._defaultBrightness = value
		else:
			_LOGGER.error("Default brightness must be between 0 and 100")

	@property
	def defaultTransition(self) -> float:
		"""The default transition time (in seconds)"""
		return self._defaultTransition
	
	@defaultTransition.setter
	def defaultTransition(self, value : float):
		if value >= 0:
			self._defaultTransition = value
		else:
			_LOGGER.error("Default transition time must be 0 or larger")
	#endregion

	async def __set_backlight_level_threadsafe(self, level):
		loop = asyncio.get_running_loop()
		await loop.run_in_executor(
			self.__transitionExecutor,
			self.__set_backlight_level, level)
		##Using a default executor for this seems to improve performance

	def __set_backlight_level(self, level):
		"""
		Args:
			level (int): A frontlight level between 0 (off) and 100 (maximum)
		"""
		if level < 0 or level > 100:
			return
		
		##Do not change this for file reading or whatever. It messes up the file and breaks the frontlight (at least for the python implementation)
		cmd = path_to_pssm_device + "/files/frontlight" + f" {level}"
		os.system(cmd)
		self._level = level

	async def __async_transition(self, brightness : int, transition: float):
		"""Async function to provide support for transitions. Does NOT perform sanity checks"""
		if self.brightness == brightness:
			return
		
		async with self._lightLock:
			min_wait = 0.05 ##Chose this value timing using timeit
			wait = transition/(abs(self.brightness-brightness))
			step = -1 if self.brightness > brightness else 1
			if wait < min_wait: 
				steps = ceil(transition/min_wait)
				_LOGGER.debug(f"Fading light from {self.brightness} to {brightness} in {transition} seconds, steps of {steps}")
				for i in range(0,steps):
					step = int(brightness - self.brightness)/(steps-i)
					await self.__set_backlight_level_threadsafe(self.brightness + step)
				await self.__set_backlight_level_threadsafe(brightness)
			else:
				_LOGGER.debug(f"Fading light from {self.brightness} to {brightness} in {transition} seconds. Waiting {wait} seconds between steps")
				while self.brightness != brightness:
					await asyncio.sleep(wait)
					await self.__set_backlight_level_threadsafe(self.brightness + step)
		
		await self.notify_condition()

	async def turn_on_async(self, brightness : int, transition: float):
		"""Async function to provide support for transitions at turn on. Does NOT perform sanity checks"""
		_LOGGER.verbose("Async turning on")
		if self.brightness == brightness:
			##Do nothing if the light is already at the correct level
			return
		
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
		
		if transition == 0:
			_LOGGER.debug(f"Setting backlight to {brightness} without transition")
			await self.__set_backlight_level_threadsafe(brightness)
			await self.notify_condition()
		else:
			self._transitionTask = asyncio.create_task(self.__async_transition(brightness, transition))
			await self._transitionTask

	def turn_on(self, brightness : int = None, transition : float = None):
		"""Turn on the backlight to the set level"""
		asyncio.create_task(self.turn_on_async(brightness, transition))

	async def turn_off_async(self, transition: float = None):
		"""Async function to provide support for transitions at turn off. Does NOT perform sanity checks"""
		_LOGGER.verbose("Async turning off")
		if not self.state:
			##Do nothing if the light is already off
			return

		if transition == None:
			transition = self.defaultTransition

		if transition < 0:
			_LOGGER.error("Transition time cannot be negative.")
			return

		if transition == 0:
			_LOGGER.debug(f"Turning backlight off without transition")
			self.__set_backlight_level(0)
			await self.notify_condition()
		else:
			self._transitionTask = asyncio.create_task(self.__async_transition(0, transition))
			await self._transitionTask

	def turn_off(self, transition : float = None):
		"""Turns off the backlight to the set level"""
		if not self.state:
			##Backlight is already off, no need to do anything
			return
		
		asyncio.create_task(self.turn_off_async(transition))

	def toggle(self, brightness : int = None, transition : float = None):
		"""Toggles the backlight, if it is off turns on to defined brightness"""
		asyncio.create_task(self.toggle_async(brightness, transition))
	
	async def toggle_async(self, brightness = None, transition = None):
		if transition == None:
			transition = self.defaultTransition

		if transition < 0:
			_LOGGER.error("Transition time cannot be negative.")
			return

		if not self._transitionTask.done():
			self._transitionTask.cancel()

		if self.state:
			await self.turn_off_async(transition)
			return
		else:
			if brightness == None:
				brightness = self.defaultBrightness
			if brightness < 0 or brightness > 100:
				_LOGGER.error(f"Brightness must be between 0 and 100. {brightness} is an invalid value")
				return
			else:
				await self.turn_on_async(brightness, transition)
		
			
class Battery(basedevice.Battery):
	'''
	The battery of the device. Provides callbacks to get the battery state and charge level, as well as update it.
	'''
	def __init__(self):

		##Ensuring the backlight is off when the dashboard starts, so the brightness and state are correct
		charge = self.readBatteryPercentage()
		state = self.readBatteryState()

		self._update_properties((charge,state))

	@property
	def percentage(self):
		"""The battery charge percentage"""
		return self._batteryPercentage
	
	@property
	def state(self):
		"""The state of the battery"""
		return self._batteryState

	async def async_update_battery_state(self):
		charge = await asyncio.to_thread(self.readBatteryPercentage())
		state = await asyncio.to_thread(self.readBatteryState())
		self._update_properties((charge,state))

	def readBatteryPercentage(self) -> str:
		with open(batteryCapacityFile) as state:
			state.seek(0)
			res = ""
			for line in state:
				res += str(line)		
		return int(res)

	def readBatteryState(self) -> str:
		res=""
		with open(batteryStatusFile) as percentage:
			percentage.seek(0)
			isFirst = True
			for line in percentage:
				if isFirst:
					res += str(line).rstrip()
					isFirst=False
		
		return res

class Network(basedevice.Network):
	'''
	Handles Network stuff. Gets IP Adress, network SSID etc, and can turn on and off wifi.
	Properties: IP, wifiOn, connected, SSID
	'''
	def __init__(self):
		self._isWifiOn = True
		self._update_network_properties()

	@property
	def IP(self) -> str:
		"""Returns the IP adress"""
		return self._IP

	@property
	def wifiOn(self) -> bool:
		"""Returns whether wifi is on"""
		return self._isWifiOn
	
	@property
	def connected(self) -> bool:
		"""Returns whether the device is connected to a wifi network"""
		return self._connected
	
	@property
	def SSID(self) -> str:
		"""Returns the SSID of the connected network"""
		return self._SSID
	
	@property
	def macAddr(self) -> str:
		"""Returns the mac adress of the device"""
		return self._macAddr

	async def async_update_network_properties(self):
		await asyncio.to_thread(self._update_network_properties)

	def update_network_properties(self):
		asyncio.create_task(self.async_update_network_properties())

	def _update_network_properties(self):
		self._macAddr = util.get_mac()
		self._connected = util.is_wifi_connected()
		if self.connected:
			self._IP = util.get_ip()
			self._SSID = util.get_SSID()
		else:
			self._IP = None
			self._SSID = None


