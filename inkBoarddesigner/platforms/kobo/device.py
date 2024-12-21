#!/usr/bin/env python

"inkBoard platform for kobo, and likely other devices with FBInk installed"

import sys
import os
import socket
import asyncio
import logging
import subprocess
import concurrent.futures
from typing import *

from pathlib import Path
from time import sleep
from math import pi, ceil
from contextlib import suppress
# Load the wrapper module, it's linked against FBInk, so the dynamic loader will take care of pulling in the actual FBInk library

#Fbink functions etc. can best be checked here: https://github.com/NiLuJe/FBInk/blob/master/fbink.h
#But this is all in C, so some translating may be needed -> yawk has an fbink mock
# Load Pillow

from PythonScreenStackManager import constants as const, devices as basedevice, tools
from PythonScreenStackManager.tools import DummyTask, TouchEvent
from PythonScreenStackManager.pssm_types import *
from PythonScreenStackManager.pssm.util import elementactionwrapper

import inkBoard.constants
from inkBoard.platforms.basedevice import BaseDevice, BaseConnectionNetwork, InkboardDeviceFeatures, FEATURES

from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import aioKIP, util, pssm_device
from .aioKIP import InputQueue
from .fbink import API as FBInk

_LOGGER = logging.getLogger(__name__)


try:
	import pywifi ##Implement pywifi rn but for the bare pssm implementation don't implement it.
	pywifi_installed = True
	_LOGGER.debug("Using pywifi")
except ModuleNotFoundError:
	pywifi_installed = False

class Device(BaseDevice, pssm_device.Device):
	"""Base class for inkBoard on kobos.

	Optionally can control the wifi interface.
	"""
	def __init__(self, name: str = pssm_device.full_device_name, rotation: RotationValues = "UR", kill_os: bool = True, refresh_rate: DurationType = "30min",
			touch_debounce_time: DurationType = aioKIP.DEFAULT_DEBOUNCE_TIME, hold_touch_time: DurationType = aioKIP.DEFAULT_HOLD_TIME, input_device_path: str = aioKIP.DEFAULT_INPUT_DEVICE):
		
		features = pssm_device.feature_list.copy()
		if pywifi_installed:
			_LOGGER.debug("Setting up connection Network")
			self._network = ConnectionNetwork()
			features.append(FEATURES.FEATURE_CONNECTION)
		else:
			_LOGGER.debug("Setting up Base Network")
			self._network = pssm_device.Network()

		##Check if these are correctly parsed when calling event bindings
		self.__KIPargs = {"input_device": input_device_path}
		self.__KIPargs["debounce_time"] = tools.parse_duration_string(touch_debounce_time)
		self.__KIPargs["long_click_time"] = tools.parse_duration_string(hold_touch_time)

		self._model = pssm_device.full_device_name
		self._name = name
		self._features = InkboardDeviceFeatures(*features)

		self._battery = pssm_device.Battery()
		self._backlight = pssm_device.Backlight(self)

		if kill_os:
			util.kill_os()
		
		tools.parse_duration_string(refresh_rate)
		self._refreshRate = refresh_rate

		FBInk.rotate_screen(rotation)
		splashscreen = inkBoard.constants.INKBOARD_FOLDER / "files" / "images" / "default_background.png"
		splash_img = ImageOps.fit(Image.open(splashscreen),(self.screenWidth,self.screenHeight))
		FBInk.fbink_print_pil(splash_img)

	#region
	##Redefining a few properties to prevent having to call the basedevice
	@property
	def colorType(self) -> Image.ImageMode:
		"Same as screenMode. Implemented for legacy purposes"
		return  self.screenMode
	
	@property
	def screenMode(self) -> Image.ImageMode:
		"The mode of images being printed on the screen"
		return "LA"
	
	@property
	def imgMode(self):
		return "RGBA"

	@property
	def screenType(self):
		return "E-Ink"
	
	@property
	def refreshRate(self) -> DurationType:
		"The interval between which the screen is fully refreshed"
		return self._refreshRate
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
		asyncio.create_task(self.refresh_loop())
		self._eventQueue = InputQueue(**self.__KIPargs)
		with suppress(asyncio.CancelledError):
			while self.Screen.printing:
				(x,y,action) = await self.eventQueue.get()
				if action == aioKIP.TOUCH_SHORT:
					touch_action = const.TOUCH_TAP
				else:
					touch_action = const.TOUCH_LONG

				await touch_queue.put(TouchEvent(x,y,touch_action))
		return

	async def refresh_loop(self):
		wait_time = tools.parse_duration_string(self.refreshRate)
		while self.Screen.printing:
			try:
				await asyncio.sleep(wait_time)
				self.refresh_screen()
			except asyncio.CancelledError:
				return
		
	async def _rotate(self, rotation=None):
		await asyncio.to_thread(FBInk.rotate_screen(rotation))
		await asyncio.to_thread(FBInk.screen_refresh())

	@elementactionwrapper.method
	def clear_screen(self):
		"Clears the entire screen"
		FBInk.screen_clear()
	
	@elementactionwrapper.method
	def refresh_screen(self, skip_clear: bool = False):
		"Refreshes the entire screen. By default clears it first"
		if not skip_clear:
			self.clear_screen()
		
		FBInk.screen_refresh()

	def set_waveform(self, mode):
		FBInk.set_waveform(mode)
	
class ConnectionNetwork(pssm_device.Network, BaseConnectionNetwork):
	def __init__(self):
		wifilogger = logging.getLogger(pywifi.__name__)
		wifilogger.setLevel(logging.WARNING)
		wifi = pywifi.PyWiFi()
		self._iface: pywifi.iface.Interface = wifi.interfaces()[0]
		profiles = self._iface.network_profiles()
		if profiles:
			self._baseprofile: pywifi.Profile = profiles[0]
		else:
			self._baseprofile = None
		super().__init__()

	def get_network_properties(self):
		##Add function to get network name

		if s := self._iface.status() == pywifi.const.IFACE_INACTIVE:
			self._isWifiOn = False
			self._connected = False
		elif s == pywifi.const.IFACE_CONNECTED:
			self._isWifiOn = True
			self._connected = True
		else:
			self._isWifiOn = True
			self._connected = False

		self._macAddr = util.get_mac()
		if self.connected:
			self._IP = util.get_ip()
			self._SSID = util.get_SSID()
		else:
			self._IP = None
			self._SSID = None

	async def async_connect(self, ssid: str = None, password: str = None):
		"""Connects to the wifi"""
		if ssid == None:
			profile = self._baseprofile
		else:
			_LOGGER.warning("Connecting to custom networks may not work")
			profile = pywifi.Profile()
			profile.ssid = ssid
			profile.auth = pywifi.const.AUTH_ALG_OPEN
			profile.akm.append(pywifi.const.AKM_TYPE_WPA2PSK)
			profile.cipher = pywifi.const.CIPHER_TYPE_CCMP
			profile.key = password
		
		await asyncio.to_thread(self.__wifi_connect, profile)

	def connect(self, ssid: str = None, password: str = None):
		asyncio.create_task(self.async_connect(ssid,password))

	def __wifi_connect(self, profile: "pywifi.Profile"):

		if profile != self._baseprofile:
			self._baseprofile = profile

		self._iface.connect(profile)
		return

	async def async_disconnect(self):
		await asyncio.to_thread(self.__wifi_disconnect)

	def disconnect(self):
		asyncio.create_task(self.async_disconnect())

	def __wifi_disconnect(self):
		self._iface.disconnect()
