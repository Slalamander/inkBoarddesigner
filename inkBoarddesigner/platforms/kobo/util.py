
import os
import logging
import socket
from typing import Optional
from pathlib import Path

from .fbink import API as FBInk

_LOGGER = logging.getLogger(__name__)

def is_wifi_connected() -> bool:
    return get_ip() != None

def get_ip() -> Optional[str]:
    """Gets the devices IP adress. Returns None if none found and sets the connected attribute appropriately"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except OSError as exce:
        _LOGGER.error(f"Error gettin IP: {exce}")
        IP = None
    finally:
        s.close()
    return IP

async def get_SSID() -> Optional[str]:
    """Gets the name of the connected wifi network. Returns Wifi off if Wifi is off """
    
    if is_wifi_connected():
        network = (os.popen("iwgetid -r").read())
        return network
    else:
        return None

async def get_mac() -> str:
    """Gets the devices mac adress"""
    ifconfig = (os.popen("ifconfig | grep eth0").read()).split()
    mac = ifconfig[-1]
    return mac

def kill_os():
    "Kills the os running on the ereader. Needs a reboot to get the os back."
    _LOGGER.info(f"Killing native {FBInk.platform} ui. Reboot the device the get it back.")
    sf = Path(__file__).parent / "scripts" / "kill-nickel.sh"
    os.system(str(sf))
    _LOGGER.info("OS killed")
