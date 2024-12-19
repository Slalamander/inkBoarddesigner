import asyncio
import logging
from typing import *
from types import MappingProxyType
import tkinter as tk
from pathlib import Path
from dataclasses import asdict
import threading

import tkthread

from PIL import Image

import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip

from PythonScreenStackManager.devices import FEATURES

from .widgets import Treeview, PSSMCanvas, BatteryFrame, BacklightFrame
from . import functions as tk_functions

from .. import const, util
from ..settings import EM_SETTINGS
from ..const import REFRESH_RATE

if TYPE_CHECKING:
    from PythonScreenStackManager.elements import Element
    from inkBoarddesigner.emulator.device import Device
    from inkBoard import core

_LOGGER = logging.getLogger(__name__)

window: "DesignerWindow"
"The main window instance"

p = Path()


class DesignerWindow(ttk.Window):
    """Specific window class meant to interface with inkBoard Designer
    
    A subclass of a ttk.Window. Sets up some base variables and functions for default behaviour.
    All calls to tkinter are automatically forwarded to the correct thread.
    """

    def __init__(self, title="ttkbootstrap", themename="litera",  size=None, position=None, minsize=None, maxsize=None, resizable=None, hdpi=True, scaling=None, transient=None, overrideredirect=False, alpha=1):
        super().__init__(title, themename, None, size, position, minsize, maxsize, resizable, hdpi, scaling, transient, overrideredirect, alpha)

        util.window = self

        window_icon = Path(__file__).parent.parent / "files" / "inkboard_designer_icon.ico"
        self.wm_iconbitmap(window_icon, window_icon)

        self._current_config_file = None

        if EM_SETTINGS.getboolean(const.DARKMODE_VAR_NAME):
            themes = (const.THEME_LIGHT,const.THEME_DARK)
        else:
            themes = (const.THEME_DARK, const.THEME_LIGHT)
        
        tk_functions.configure_themes(themes)
        self.style.theme_use(themes[-1])

        self.__state = ""
        self.__loaded_event = asyncio.Event()

        self._mainLoop: asyncio.BaseEventLoop = None
        self._inkBoard_thread: threading.Thread = None
        self._inkBoard_clean = True 
        #Indicates the last inkBoard thread was cleaned up (i.e. fully reloaded)

        self._inkBoard_lock = threading.Lock()
        "Lock to ensure only one inkBoard lock runs at a time"

        self._darkmode_variable = tk.BooleanVar(self, value=EM_SETTINGS.getboolean(const.DARKMODE_VAR_NAME), name=const.DARKMODE_VAR_NAME)
        self._saveasvariable = tk.BooleanVar(self, value=EM_SETTINGS.getboolean(const.SAVEAS_VAR_NAME), name=const.SAVEAS_VAR_NAME)
        self._hightlight_variable = tk.BooleanVar(self, value=EM_SETTINGS.getboolean(const.HIGHLIGHT_VAR_NAME), name=const.HIGHLIGHT_VAR_NAME)

        self._tree_list_variable = ttk.StringVar(self, name=const.LIST_VAR_NAME, 
                                                value=const.NO_TREE_OPTION)

        self._window_update_task : asyncio.Task = None
        self._resizeTask: asyncio.Task = util.DummyTask()
        
        self._screenCanvas = PSSMCanvas(self, name=const.CANVAS_NAME, cursor="target")
        self._screenCanvas.pack(fill=tk.BOTH, side=tk.LEFT)

        self._background_Tk_idx = None

        self._resize_bind = None
        self._width = self.winfo_width()
        self._height = self.winfo_height()
        self.bind("<Configure>", self._configure, add="+")

        self._reloading = True

        self.interface_buttons : list[ttk.Button] = []

        vars = (self._darkmode_variable, self._saveasvariable, self._hightlight_variable, self._tree_list_variable)

        for var in vars:
            var.trace_add("write", self.trace_variable)

        self._buttonLabel: ttk.Label

        self._progressframe = ttk.Frame(self.screenCanvas, bootstyle=ttk.SECONDARY)
        
        self._progressTitle = ttk.Label(self._progressframe, font=const.DEFAULT_LABEL_FONT, text="Loading emulator", 
                                    style=f"{ttk.PRIMARY}.{const.LOADBAR_LABEL_STYLE}")
        self._progressBar = ttk.Progressbar(self._progressframe, bootstyle=(ttk.STRIPED, ttk.PRIMARY))
        self._progressText = ttk.Label(self._progressframe, style=const.LOADBAR_LABEL_STYLE)

        self._progressTitle.pack(side=tk.TOP)
        self._progressBar.pack(side=tk.TOP, fill=tk.X, padx=(10,10))
        self._progressText.pack(side=tk.BOTTOM)

    #region
    @property
    def hightlight_variable(self) -> tk.BooleanVar:
        "The variable tracking the highlight setting"
        return self._hightlight_variable
    
    @property
    def saveas_variable(self) -> tk.BooleanVar:
        "Variable tracking if the screenshots should show a dialog box before saving"
        return self._saveasvariable
    
    @property
    def darkmode_variable(self) -> tk.BooleanVar:
        "Variable tracking if darkmode is on"
        return self._darkmode_variable
    
    @property
    def tree_list_variable(self) -> ttk.StringVar:
        "Variable tracking which tree is to be displayed"
        return self._tree_list_variable
    
    @property
    def screenCanvas(self) -> PSSMCanvas:
        "Canvas that the PSSM screen prints onto"
        return self.children[const.CANVAS_NAME]

    @property
    def buttonFrame(self) -> ttk.LabelFrame:
        "Frame holding the main buttons"
        return self._buttonFrame
    
    @property
    def settingsFrame(self) -> ttk.LabelFrame:
        "Frame holding the settings widgets"
        return self._settingsFrame

    @property
    def treeFrame(self) -> "TreeFrame":
        "The frame holding the treeviews"
        return self._treeFrame
    
    @property
    def configLabel(self) -> ttk.Label:
        "The button to indicate the loaded config"
        return self._configLabel
        
    @property
    def state(self) -> Literal[ttk.ACTIVE, ttk.DISABLED]:
        "Current state of the interface. Disabled means certain widgets are disables."
        return self.__state

    @property
    def loaded(self) -> bool:
        "Whether an inkBoard config has been successfully loaded and is currently running"
        return self.__loaded_event.is_set()
    #endregion


    async def run_update_loop(self):
        "Starts the update loop. Relatively akin to running to running window.Mainloop, but async"
        self._mainLoop = asyncio.get_running_loop()
        util.main_loop = asyncio.get_running_loop()
        self._window_update_task = asyncio.create_task(self._update_loop(), name="designer-window-loop")
        try:
            await self._window_update_task
        except asyncio.CancelledError:
            pass
        return

    async def _update_loop(self):
        sleep_time = 1/REFRESH_RATE
        try:
            while True:
                    self.update()
                    await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            self.destroy()
            return

    def stop_update_loop(self):
        "Stops the window update loop, and destroys it if running. **Does not handle actually quitting the programme!**"
        if self._window_update_task:
            self._window_update_task.cancel()

    def call_in_main_thread(self, func : Callable, *args, **kwargs):
        """Helper function that allows calls function `func` with arguments `args` and keyword arguments `kwargs` in the main loop.

        Needed since tkinter doesn't like having window settings changed in different threads.
        Does not work with Coroutines.
        Keep in mind a blocking function blocks the main thread, which means the window becomes unresponsive.
        """

        return util.call_in_main_thread(func, args, kwargs)

    def _configure(self, event : tk.Event):
        if event.widget != self:
            return
        
        if event.width != self._width or event.height != self._height:
            if abs(1 - (event.width/self._width)) > 0.05 or abs(1 - (event.height/self._height)) > 0.05:
                ##Larger increase than this: assume toggle fullscreen, so update right asap
                if self._resizeTask.done():
                    resize_event = None
                else:
                    return
            else:
                if not self._resizeTask.done():
                    return
                resize_event = asyncio.Event(loop=self._mainLoop)
                self._resize_bind = self.bind("<ButtonRelease-1>", lambda event: resize_event.set(), add="+") ##Won't add this to bind as it is removed upon releasing the mouse button

            if not self._mainLoop:
                self.screenCanvas._build_canvas_background()
                return
            
            self._resizeTask = self._mainLoop.create_task(self._resize(resize_event))
        return

    async def _resize(self, event : Union[tk.Event,asyncio.Event]):
        if event == None:
            pass
        elif isinstance(event,asyncio.Event):
            #The timeout may not really be needed since it seems resizing blocks the event loop anyways
            #But just to be sure it's useful to have imo
            _, pending = await asyncio.wait([event.wait()],timeout=0.25)
            if pending:
                event.set()
            self.unbind("<ButtonRelease-1>")
        else:
            return
        
        self._width = self.winfo_width()
        self._height = self.winfo_height()

        self._screenCanvas["width"] = self._width - const.INTERFACE_WIDTH
        self._screenCanvas["height"] = self._height
        self.screenCanvas.update()  ##Gotta update the canvas first to ensure it gathers the right size.
        self.screenCanvas._build_canvas_background()

        self.unbind("<ButtonRelease-1>", self._resize_bind)
        self._resize_bind = None
        return

    def setup_canvas(self, size):
        "Performs the inital canvas setup by configuring the width and creating the background image"
        return self.__setup_canvas(self, size)

    @tkthread.called_on_main
    def __setup_canvas(self, size):
        "Performs the inital canvas setup by configuring the width and creating the background image"

        self._screenCanvas["width"] = size[0]
        self._screenCanvas["height"] = size[1]

        self.screenCanvas._build_canvas_background()
        return self._screenCanvas
        
    
    def clear_canvas(self, *args):
        "Clears the screen canvas from everything except the background"
        tkthread.call_nosync(self.screenCanvas._clear)


    def set_progress_bar(self, value, text=None, title=None):
        self._set_progress_bar(self, value, text, title)
        return
    
    @tkthread.called_on_main
    def _set_progress_bar(self, value, text, title=None):
        
        if value == ttk.DANGER:
            self._progressBar.configure(bootstyle=(ttk.STRIPED, ttk.DANGER))
            self._progressTitle.configure(style=f"{ttk.DANGER}.{const.LOADBAR_LABEL_STYLE}")
            if text:
                self._progressText["text"] = text
            return
        
        if value < 0:
            self._progressframe.place_forget()
            self._progressText["text"] = ""
            self._progressTitle["text"] = ""
            self._progressBar["value"] = 0
            self._progressBar.configure(bootstyle=(ttk.STRIPED, ttk.PRIMARY))
            self._progressTitle.configure(style=f"{ttk.PRIMARY}.{const.LOADBAR_LABEL_STYLE}")
            return
        
        if value >= 100:
            async def hide_progress_bar():
                await asyncio.sleep(0.5)
                self.set_progress_bar(-1,"")
            self._mainLoop.create_task(hide_progress_bar())

        self._progressBar["value"] = value
        if text:
            self._progressText["text"] = text
        if title:
            self._progressTitle["text"] = title

        if not self._progressframe.winfo_viewable():
            self._progressframe.place(relx=0.25, rely=0.5,
                                    relwidth=0.5, height=100)
            self._progressframe.update()
            self._progressText.configure(wraplength=self._progressframe.winfo_width())
    
    def set_inkboard_state(self, state: Literal[ttk.ACTIVE, ttk.DISABLED, ttk.DANGER, "ERROR"]):
        "Sets the state of the inkBoard connected widgets"

        if state and state.upper() == "ERROR": 
            state = ttk.DANGER

        if state == self.__state:
            return
        
        self.__state = state
        if state in {ttk.DISABLED, None}:
            self._set_disabled_state(self)
            if state == None:
                self._set_config_label(self, state)
        elif state == ttk.ACTIVE:
            self._set_active_state(self)
        elif state == ttk.DANGER:
            self._set_button_state(self, ttk.DANGER)
            self._set_progress_bar(self, state, text=None)


    @tkthread.called_on_main
    def _set_disabled_state(self):
        #Set when no config is currently (succesfully) loaded
        self.__loaded_event.clear()
        self._set_button_state(self, ttk.DISABLED)
        self.clear_canvas()
        self.treeFrame._clean_up()
        self.set_progress_bar(-1)

    @tkthread.called_on_main
    def _set_active_state(self):
        self.__loaded_event.clear()
        self._set_button_state(self, ttk.ACTIVE)
        self.treeFrame._setup()
        return

    @tkthread.called_on_main
    def _set_button_state(self, state: Literal[ttk.ACTIVE, ttk.DISABLED, ttk.DANGER]):
        
        if state == ttk.DANGER:
            set_buttons = filter(lambda x: x.winfo_name() in const.ERROR_ACTIVE_BUTTONS, self.interface_buttons)
            button_state = ttk.ACTIVE
            self._set_config_label(self, state)
        else:
            set_buttons = self.interface_buttons
            button_state = state

        for button in set_buttons:
            button.configure(state=button_state)    #@IgnoreException

        self.treeFrame.list_menu.configure(state=button_state)
        self._set_config_label(self, state)

    @tkthread.called_on_main
    def _set_config_label(self, state):
        
        ##Use this one too to set the label to error style if loading the config errors.
        if state == ttk.ACTIVE:
            frame_state = ttk.PRIMARY
        elif state == ttk.DISABLED:
            frame_state = ttk.SECONDARY
        elif state == ttk.DANGER:
            frame_state = state
        elif state == None:
            self._current_config_file = None
            self.configLabel.pack_forget()
            self._buttonLabel.pack(side=tk.LEFT, fill=tk.X, expand=1)
            return

        self._buttonLabel.pack_forget()
        self.configLabel.pack(side=tk.LEFT, fill=tk.X, expand=1)
        self.configLabel.configure(style=f"{frame_state}.TLabel")

    def trace_variable(self, var_name, *args):
        newVal = window.globalgetvar(var_name) 
        EM_SETTINGS[var_name] = str(newVal)
        return

class TreeFrame(ttk.Frame):

    tree: ttk.Treeview
    "The current treeview widget"

    _window: DesignerWindow

    def __init__(self, master = None, **kwargs):
        super().__init__(master, **kwargs)

        self._base_trees = {"none": None}
        
        self.__current_tree_option = "none"
        self.__tree = None


        self.__registered_trees = {}

        self.bind("<Leave>", self._leave)

        scrollbar = ttk.Scrollbar(self, orient="vertical",
                                style=const.SCROLLBAR_STYLE)
        self.__scrollbar = scrollbar

        self.__base_options = (const.NO_TREE_OPTION, const.ELEMENT_TREE_OPTION)
        self.list_menu["values"] = self.__base_options
        self.list_menu.bind('<<ComboboxSelected>>', self._select_tree)
        
        val = EM_SETTINGS.get(const.LIST_VAR_NAME)
        self._setup_value = val

        self.list_menu.set(const.NO_TREE_OPTION)
        Treeview._treeframe = self
        return

    #region
    @property
    def tree(self) -> Optional[Treeview]:
        return self.__tree

    @property
    def current_option(self) -> str:
        "The currently selected option in the menu list"
        val_idx = self.list_menu.current()
        return self.list_menu["values"][val_idx]

    @property
    def current_tree_option(self) -> str:
        return self.__current_tree_option

    @property
    def list_menu(self) -> ttk.Combobox:
        "Menu holding the tree options"
        return window._list_menu

    @property
    def scrollbar(self) -> ttk.Scrollbar:
        "Scrollbar to scroll through trees"
        return self.__scrollbar

    @property
    def registered_trees(self) -> dict[str,Treeview]:
        return self._base_trees | self.__registered_trees

    @property
    def entity_tree(self) -> Treeview:
        return self.children[const.ENTITY_TREE_NAME]
    
    @property
    def element_tree(self) -> Treeview:
        return self._element_tree
    #endregion

    def _select_tree(self, event: tk.Event):
        val = self.current_option
        self.show_tree(val)
        return

    def show_tree(self, option: str):
        option = option.lower()
        if option not in self.registered_trees:
            _LOGGER.warning(f"No tree registered under option {option}")
            return
        
        new_tree = self.registered_trees[option]

        if self.tree:
            self.tree.pack_forget()
            self.tree.tooltip.hide_tip()
        else:
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.__current_tree_option = option
        self.__tree = new_tree

        if not new_tree:
            self.scrollbar.pack_forget()
            return
        
        new_tree.pack(in_ = self ,anchor=tk.S, fill=tk.BOTH, expand=1)
        self.scrollbar.configure(command=new_tree.yview)
        new_tree.configure(yscrollcommand=self.scrollbar.set)
        
        return

    def register_tree(self, tree_option: str, widget: Treeview):

        tree_option = tree_option.lower()
        assert isinstance(widget, Treeview), "Tree widget must be an inkBoard Treeview"
        assert tree_option not in self.registered_trees, f"A treewidget under option {tree_option} is already registered"

        self.__registered_trees[tree_option.lower()] = widget
        ops = list(self.list_menu["values"])
        ops.append(tree_option.title())
        self.list_menu["values"] = ops

    def get_current_tree(self) -> Optional[Treeview]:
        return self.tree
    
    def get_tree(self, tree_option: str) -> Treeview:
        option = tree_option.lower()
        if option == const.ELEMENT_TREE_OPTION.lower():
            return self._element_tree
        
        if option not in self.registered_trees:
            _LOGGER.warning(f"No tree registered under option {option}")
            return
        return self.registered_trees[option]

    def _leave(self, event):
        
        for tree in self.registered_trees.values():
            if tree == None: continue
            tree.tooltip.hide_tip()

    def _clean_up(self):
        _LOGGER.debug("Cleaning up treeframe")
        if self.tree:
            self.tree.disable()

        if hasattr(self, "_old_register"):
            self._setup_value = self.list_menu.get()

        self.list_menu.configure(state=ttk.DISABLED)

        self._old_register = self.__registered_trees.copy()
        self.__registered_trees = {}    ##Emptying this does remove the tree entirely. Maybe make a copy for an old_register?

        self.list_menu["values"] = self.__base_options
        self._element_tree: Treeview
        self._element_tree.delete(*self._element_tree.get_children())

    def _setup(self):
        
        self.list_menu.configure(state=ttk.READONLY)
        list_val = self._setup_value
        self._old_register = {}
        if list_val.lower() in self.registered_trees:
            tree_option = list_val
        else:
            tree_option = const.NO_TREE_OPTION

        self.list_menu.set(tree_option)
        self.show_tree(tree_option)
        self._old_register = {}
        return

class _AdditionalWindow(ttk.Toplevel):
    ##Used for additional windows of which only 1 instance is supposed to be open.

    _instance: "ElementWindow" = None

    __instances = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance:
            try:
                cls._instance.destroy()
            except:
                pass
            cls._instance = None
        cls._instance = super().__new__(cls)
        _AdditionalWindow.__instances[cls] = cls._instance
        return cls._instance

    @classmethod
    def close_all(cls):
        for instance_cls, instance in cls.__instances.items():
            if instance != None:
                try:
                    instance.destroy()
                except:
                    pass
            cls.__instances[instance_cls] = None
            instance_cls._instance = None
        return        


class ElementWindow(_AdditionalWindow):
    
    def __init__(self, element: "Element", **kwargs):

        self._element = element
        title = f"{element.__class__.__name__}: {element.id}"

        super().__init__(title, master=window,  **kwargs)

        elt_text = self.create_element_attribute_list()

        ##will probably turn this into a grid instead of using pack.

        text_widget = ttk.ScrolledText(self)
        text_widget.insert("0.0", elt_text)
        text_widget.configure(state=ttk.DISABLED)
        text_widget.grid(row=0, column=0, columnspan=2)
        img_button = ttk.Button(self,text="Show Image", command=self.show_element_image)
        img_button.grid(row=1, column=0)
        ToolTip(img_button,const.SHOW_IMAGE_TIP, const.TOOLTIP_STYLE)

        save_button = ttk.Button(self,text="Save Image", command=self.save_element_image)
        save_button.grid(row=1, column=1)
        ToolTip(save_button,const.SAVE_IMAGE_TIP, const.TOOLTIP_STYLE)

        self._img_button = img_button

        return

    def create_element_attribute_list(self) -> str:
        
        elt = self._element
        text = ""
        for attr in dir(elt):
            if attr[0] == "_":
                continue

            if attr == "id":
                continue

            if not hasattr(elt,attr):
                continue

            val = getattr(elt,attr,False)
            if callable(getattr(elt,attr)):
                continue
            
            if isinstance(val,(bool,str,int,float,dict,MappingProxyType, set, type(None))):
                pass
            elif isinstance(val,(list,tuple)):
                t = type(val).__name__
                val = str(val)
                if len(val) > 50:
                    val = f"{t}: [...]"
            else:
                val = val.__class__.__name__
                v = val

            text = text + "\n" + "   " + f"{attr}: {val}"
        return text

    def show_element_image(self, *args):
        
        if isinstance(self._element.imgData,Image.Image):
            self._element.imgData.show()

    def save_element_image(self, *args):
        
        if isinstance(self._element.imgData,Image.Image):
            img = self._element.imgData.copy()
            tk_functions.save_image(img, f"{self._element.id}_")

class DeviceWindow(_AdditionalWindow):
    
    def __init__(self, device: "Device", **kwargs):

        self._device = device
        if device == None:
            title = "Emulated Device"
            device_text = "No device being emulated"
        else:
            title = device._model
            device_text = self.create_device_text(device)

        super().__init__(title, master=window,  **kwargs)

        feature_pad_x = (10,10)
        h = device_text.count("\n") + 2

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1, pad=10)

        if device != None:
            feature_col = 0
            feature_row = 1
            if device.has_feature(FEATURES.FEATURE_BATTERY):
                BatteryFrame(self, device).grid(sticky=ttk.NSEW, padx=feature_pad_x,
                                                            row=feature_row, column=feature_col)
                feature_col += 1

            if device.has_feature(FEATURES.FEATURE_BACKLIGHT): 
                if feature_col != 0:
                    self.add_seperator(feature_row, feature_col)
                    feature_col += 1

                BacklightFrame(self, device).grid(sticky=ttk.NSEW, padx=feature_pad_x,
                                                            row=feature_row, column=feature_col)
                feature_col += 1

        textw = ttk.Text(self, height = h)
        textw.insert("0.0", device_text)
        textw.configure(state=ttk.DISABLED)
        textw.grid(sticky=ttk.NSEW, pady=(5,10),
                row=0, column=0, columnspan=feature_col)

    def create_device_text(self, device: "Device"):
        text = f"{device.model}"
        
        attr_list = {"Platform": "_emulated_platform", "Model": "model", "Screen type": "screenType", 
                    "Width": "width", "Height": "height"}

        for t, attr in attr_list.items():
            val = getattr(device,attr,None)
            text = f"{text}\n    {t}: {str(val)}"
        
        feature_text = ""
        for feature, val in asdict(device._features).items():
            if val: 
                if feature_text:
                    feature_text = f"{feature_text}, {feature}"
                else:
                    feature_text = f"{feature}"
        
        text = f"{text}\n    Features: {feature_text}"

        return text
    
    def add_seperator(self, row, col):
        sep = ttk.Separator(self,orient="vertical", bootstyle=const.FEATURE_FRAME_STYLE)
        sep.grid(row=row, column=col, sticky=ttk.NSEW, pady=(0,10))

class ConfigWindow(_AdditionalWindow):

    def __init__(self, core: "core", **kwargs):
        ##Need to determine what to show in this window
        ##At least: config name; platform; loaded integrations
        ##Also: allow for installing integration/platform requirements from here
        ##Likely: also the ui to run examples

        self._core = core

        super().__init__("Configuration", **kwargs)
        label = ttk.Label(self, text=self.gather_integrations(), 
                        font=('Arial Bold', 10),
                        bootstyle=ttk.PRIMARY)

        label.pack()

    def gather_integrations(self):
        if not hasattr(self._core, "config"):
            text = "No config loaded"
            return text

        text = self._core.config.filePath.name
        return text


