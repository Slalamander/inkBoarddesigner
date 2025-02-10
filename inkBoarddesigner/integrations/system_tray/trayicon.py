
from typing import TYPE_CHECKING
import threading
import asyncio

from PIL import Image
from pathlib import Path

import pystray

import inkBoard
from inkBoard.constants import INKBOARD_ICON
from inkBoard.helpers import QuitInkboard, ParsedAction

from . import system_tray_entry, TRAYSIZE, TOLERANCE

if TYPE_CHECKING:
    from inkBoard import CORE as CORE, config
    from inkBoarddesigner.platforms.desktop import device as desktop

_LOGGER = inkBoard.getLogger(__name__)

default_config = system_tray_entry(icon="circle", hide_window=True, toolwindow=False)

class HIDEACTIONS:
    ICONIFY = "iconify"
    WITHDRAW = "withdraw"


class TrayIcon(pystray.Icon):

    def __init__(self, core: "CORE", config: "config", **kwargs):
        self.__core = core
        tray_config = config["system_tray"]
        
        if not tray_config:
            tray_config = default_config
        else:
            tray_config = default_config.copy() | tray_config

        if tray_config.get("hide_window", False):
            if core.DESIGNER_RUN:
                _LOGGER.info("Not running system_tray with hide_window in the designer")
                self._minimise_action = HIDEACTIONS.ICONIFY
            else:
                self._minimise_action = HIDEACTIONS.WITHDRAW
        else:
            self._minimise_action = HIDEACTIONS.ICONIFY
        ##Other options to add: custom icon; custom name

        self._toolwindow = tray_config.get("toolwindow", False)

        self._tray_size = tray_config.get("tray_size", TRAYSIZE)

        if tray_config["icon"] == "circle":
            imgfile = Path(__file__).parent / "files" / f"icon_circle.ico"
        elif tray_config["icon"] == "droplet":
            imgfile = Path(__file__).parent / "files" / f"icon_droplet.ico"
        else:
            imgfile = Path(tray_config)
        img = Image.open(imgfile)

        extra_action = ParsedAction({"action" :"custom:open_log_window", "data": {"level": "DEBUG"}}, awaitable=False)
        ##Currently throws error for this cause is coro
        ##Add option such that it automatically wraps a coroutine into a task
        ##(i.e. the result of the action is not used)

        menu = pystray.Menu(
            pystray.MenuItem(
                text="Minimise", action = self.minimise_window,
                default=True, visible=False
                ),
            pystray.MenuItem(
                text="Reload", action = self._reload_inkboard
            ),
            pystray.MenuItem(
                text="Quit", action = self._quit_inkboard
            ),
            pystray.MenuItem(text="Test Action", action=lambda item: extra_action())
        )
        super().__init__("inkBoard", img, "inkBoard", menu, **kwargs)
        if self._toolwindow:
            self.window.withdraw()

    @property
    def _device(self) -> "desktop.Device":
        return self.__core.device

    @property
    def window(self):
        return self._device.window
    
    def minimise_window(self, item):
        "Minimise the dashboard window"
        self._device._call_in_main_thread(self._minimise_window, item)

    def _minimise_window(self, item):
        "Minimises the window. Must be called in the main thread"
        _LOGGER.debug(f"Minimising window via {item}")

        # self.window.update()
        x = self.window.winfo_pointerx()
        y = self.window.winfo_pointery()
        s = self.window.wm_state()
        

        if self._toolwindow:
            if self.window.wm_state() != "normal": self.window.deiconify()
            self.window.focus_force()
            self._set_window_position(x,y)
            self.window.update()
            return
        
        if self.window.wm_state() != "normal":
            if self._minimise_action == HIDEACTIONS.WITHDRAW:
                ##This simply makes the animation of the window appearing a lot smoother
                self.window.iconify()
            self.window.deiconify()
            self._set_window_position(x,y)
        else:
            if self._minimise_action == HIDEACTIONS.ICONIFY:
                self.window.withdraw()
            else:
                self.window.iconify()

        # self.window.focus_force()

        self.window.update()

    def _set_window_position(self, x, y):


        window = self.window

        w = window.winfo_width()
        h = window.winfo_height()

        win_x = None
        win_y = None

        (sw, sh) = (window.winfo_screenwidth(), window.winfo_screenheight())
        _LOGGER.verbose(f"Clicked on {(x,y)}, screen size is {(sw, sh)}")

        if x >= sw - TOLERANCE*self._tray_size:
            ##Should be on the right of screen
            win_x = sw - w - self._tray_size
        elif x <= TOLERANCE*self._tray_size:
            ##Tray is on the left of screen
            win_x = self._tray_size

        if y >= sh - TOLERANCE*self._tray_size:
            ##Tray is on bottom of screen
            win_y = sh - self._tray_size - h
        elif y <= TOLERANCE*self._tray_size:
            ##Tray is on the top of screen
            win_y = self._tray_size

        if win_x == None and win_y == None:
            _LOGGER.error(f"Cannot determine location of the system tray from click coordinates {(x,y)}")
            return
        elif win_y == None and win_x != None:
                cy = y - 2*self._tray_size
                if cy <= 0:
                    ##align window to top
                    win_y = 0
                elif cy + h >= sh:
                    ##Align window to bottom
                    win_y = sh - h
                else:
                    win_y = cy
        elif win_x == None and win_y != None:
            cx = x - 2*self._tray_size
            if cx <= 0:
                ##align window to top
                win_x = 0
            elif cx + w >= sw:
                ##Align window to bottom
                win_x = sw - w
            else:
                win_x = cx


        new_geo = f"{w}x{h}+{win_x}+{win_y}"
        _LOGGER.verbose(f"Repositioning window via tray location to {(win_x,win_y)}")
        window.wm_geometry(new_geo)
        ##If this turns out to not work for any other alignments than having a bottom taskbar:
        ##Apparently microsoft removed the option to move the taskbar to a different edge of the screen (why???)
        ##Since I always had it on the bottom, I did not know this. I may test it at a future point, but if anyone else tests it and can confirm it to be working, that would be great :)

    def _reload_inkboard(self, item):
        self.__core.screen.reload()
        self.stop()
    
    def _quit_inkboard(self, item):
        self.__core.screen.quit(QuitInkboard("Quit via systemtray"))
        self.stop()

    def start(self):
        if self._toolwindow:
            if self.__core.DESIGNER_RUN:
                _LOGGER.info("Hiding the designer from the taskbar is disabled")
            else:
                self.window.update_idletasks()
                self.window.wm_attributes("-toolwindow", True)
                self.window.overrideredirect(True)
                
        self.run_detached()

