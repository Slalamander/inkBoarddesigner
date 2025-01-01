
from typing import TYPE_CHECKING

from PIL import Image
from pathlib import Path

import pystray

import inkBoard
from inkBoard.constants import INKBOARD_ICON
from inkBoard.helpers import QuitInkboard

if TYPE_CHECKING:
    from inkBoard import core as CORE
    from inkBoarddesigner.platforms.desktop import device as desktop

_LOGGER = inkBoard.getLogger(__name__)

iconname = "circle"
imgfile = Path(__file__).parent / "files" / f"icon_{iconname}.ico"

img = Image.open(imgfile)

class TrayIcon(pystray.Icon):

    def __init__(self, core: "CORE", name, icon=None, title=None, menu=None, **kwargs):
        self.__core = core
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
        )
        super().__init__("inkBoard", img, "inkBoard", menu, **kwargs)

    @property
    def _device(self) -> "desktop.Device":
        return self.__core.device

    @property
    def window(self):
        return self._device.window
    
    def minimise_window(self, item):
        _LOGGER.debug(f"Minimising window via {item}")

        if self.window.wm_state() != "normal":
            if self.window.wm_state() == "withdrawn":
                ##This simply makes the animation of the window appearing a lot smoother
                self.window.iconify()
            self.window.deiconify()
        else:
            self.window.withdraw()
        
        self.window.update()

    def _reload_inkboard(self, item):
        self.__core.screen.reload()
        self.stop()
    
    def _quit_inkboard(self, item):
        self.__core.screen.quit(QuitInkboard("Quit via systemtray"))
        self.stop()