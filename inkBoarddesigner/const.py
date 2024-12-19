import pkgutil
from pathlib import Path

import ttkbootstrap as ttk

from inkBoard.constants import INKBOARD_COLORS, ARGUMENT_CONFIG
from PythonScreenStackManager.devices.const import CANVASNAME

PSSM_FOLDER = Path(pkgutil.get_loader("PythonScreenStackManager").get_filename()).parent
INKBOARD_FOLDER = Path(pkgutil.get_loader("inkBoard").get_filename()).parent

IMPORTER_THREADPOOL = "designer-importer-threadpool"
BASE_WINDOW_TASK_NAME = "designer-window"

INTEGRATION_DIRS = {
    f"{__package__}.integrations": Path(__file__).parent / "integrations",
    "inkBoard.integrations": INKBOARD_FOLDER / "integrations",
}

##The last one is for the custom integrations. Will be added later on.
##Considering how taking precedent works: probably use the custom folder first.

DEFAULT = "default-designer-value"
"constant to mark default values"

RELOAD_MODULES = [
    "emulator"
]

for i, mod in enumerate(RELOAD_MODULES):
    RELOAD_MODULES[i] = f"{__package__}.{mod}"

HIGHLIGHT_VAR_NAME = "hightlight" ##These have to correspond to the value in the settings
SAVEAS_VAR_NAME = "saveas"
DARKMODE_VAR_NAME = "darkmode"

LIST_VAR_NAME = "treeview-list-variable" ##Maybe this one not but will have to see obviously
ELEMENT_TREE_OPTION = "Elements"
NO_TREE_OPTION = "None"

CANVAS_NAME = CANVASNAME
SCREEN_TAG = "pssm-screen"
UI_FRAME_NAME = "designer-ui-frame"
TREE_FRAME_NAME = "treeview-frame"
HOVER_TAG = "treeview-item-hover"

SCREENSHOT_BUTTON_NAME = "config-button-capture"
SCREENSHOT_BUTTON_TEXT = "Capture"
SCREENSHOT_BUTTON_ICON = "mdi:camera-iris"

PACK_BUTTON_NAME = "config-button-pack"
PACK_BUTTON_TEXT = "Pack"
PACK_BUTTON_ICON = "mdi:folder-download"

RELOAD_BUTTON_NAME = "config-button-reload"
RELOAD_BUTTON_TEXT = "Reload"
RELOAD_BUTTON_ICON = "mdi:sync-circle"

STOP_BUTTON_NAME = "config-button-stop"
STOP_BUTTON_TEXT = "Stop"
STOP_BUTTON_ICON = "mdi:close-circle"

ERROR_ACTIVE_BUTTONS = [STOP_BUTTON_NAME, RELOAD_BUTTON_NAME]
"Buttons that should stay active if loading inkBoard errored"

THEME_DARK = "darkly"
THEME_LIGHT = "yeti"
TREEVIEW_STYLE = "custom.Treeview"
SCROLLBAR_STYLE = "dark.Round.Vertical.TScrollbar"
FEATURE_FRAME_STYLE = ttk.PRIMARY
LOADBAR_LABEL_STYLE = "loadbar.TLabel"

BUTTON_STYLE = "custom.TButton"
TOOLTIP_STYLE = (ttk.DARK, ttk.INVERSE)

INTERACT_CURSOR = "hand2"

ICON_COLOR = INKBOARD_COLORS["inkboard"]
HA_BLUE: tuple = (3, 169, 244, 255)
#Color used for home assistant branding

REFRESH_RATE = 20 #Rate to refresh the window per second (Idk if this updates the canvas too, may indeed update all widgets)

DEFAULT_LABEL_FONT = ('Arial Bold', 10)

INTERFACE_PADDING = 0.04
INTERFACE_BORDER = 5
INTERFACE_WIDTH = 250
BUTTON_HEIGHT = 30
BUTTON_FONT_SIZE = 16
BUTTON_WIDTH = int(INTERFACE_WIDTH*0.36)
BUTTON_ICON_COLOR = ICON_COLOR

SETTINGS_HEIGHT = int(INTERFACE_WIDTH*0.3)
SETTINGS_WIDTH = int(INTERFACE_WIDTH/4)
SETTINGS_PADDING = 5
LIST_WIDTH = 20 #This value is gotten via trial and error, for an INTERFACE_WIDTH of 200; tkinter width's are just kind of an illusion generally
DEFAULT_LIST_OPTIONS = ["None", "Elements"]

HA_FONT_NAME = "Quicksand-bold.ttf"
HA_FONT_FILE = PSSM_FOLDER / "fonts" / HA_FONT_NAME


SCREENSHOT_TIP = "Make a screenshot of the currently shown dashboard"
PACK_TIP = "Make an update/install package of the currently running config (Not implemented)"
RELOAD_TIP = "Reload the configuration and inkBoard instance."
STOP_TIP = "Stop the emulator and close the current config."
SHOW_IMAGE_TIP = "Show the current image of the element in your default image viewer."
SAVE_IMAGE_TIP = "Save the current element image as a file. Follows the value of the 'Save As' setting on whether or not to show a file dialog."
CONFIG_LABEL_TIP = "Open the folder of the current config in your file explorer."
CONFIG_OPEN_TIP = "Choose a config file to run."

DARKMODE_TIP = "Toggle Dark Mode"
HIGHLIGHT_TIP = "Highlight elements in the dashboard when selecting them in the entity or element list"
SAVEAS_TIP = "Show a file explorer window when making a screenshot"
TREE_REFRESH_TIP = "Refresh the current treeview"

CONFIG_OPTIONS_TIP = "Info on the currently opened config (if any), or open a new config."
DEVICE_TIP = "Info on the currently running device (if any), as well as some settings to alter emulation behaviour."

DEFAULT_ELEMENT_ICON = "mdi:shape"
TREEVIEW_ICON_SIZE = (15,15)

HIGHLIGHT_DASH = (5,2)
HIGHLIGHT_WIDTH = 5
HIGHLIGHT_COLOR = "red"