
import asyncio
from typing import *
import tkinter as tk
import logging
from pathlib import Path
from PIL import Image, ImageOps

from mdi_pil import mdiType
from mdi_pil.ttkbootstrap_mdi import PhotoIcon, MDIIcon

import ttkbootstrap as ttk
from ttkbootstrap.style import Bootstyle
from ttkbootstrap.tooltip import ToolTip

from . import functions as tk_functions
from .. import const
from ..util import iidType

if TYPE_CHECKING:
    from .windows import DesignerWindow
    from ..emulator.device import Device

    from PythonScreenStackManager.elements import Element

_LOGGER = logging.getLogger(__package__)
_LOGGER.setLevel(logging.DEBUG)

_LOGGER = logging.getLogger(__package__)
_LOGGER.setLevel(logging.DEBUG)

window: "DesignerWindow"

class LabelToggle(ttk.Labelframe):

    "Labelframes with a toggle widget inside. Use the noframe.TLabelframe style defined in configure_themes"

    def __init__(self, master = None, *, labelanchor = "w", cursor = const.INTERACT_CURSOR, style="noframe.TLabelframe",
                variable: tk.BooleanVar = None, command = "", **kwargs):
        super().__init__(master, cursor=cursor, labelanchor=labelanchor, style=style, **kwargs)        
        
        self.columnconfigure(0,weight=1)
        self.columnconfigure(1,weight=1)
        self.columnconfigure(2,weight=1)

        self.variable: Optional[tk.BooleanVar] = variable
        self._command = command

        b = self.cget("style")
        bootstyle = Bootstyle.ttkstyle_widget_color(b)
        if not bootstyle: bootstyle="primary"

        self.CheckButton = ttk.Checkbutton(self,
                onvalue = 1, offvalue = 0, bootstyle=f"{bootstyle}-round-toggle",
                variable=self.variable, command=command, cursor=cursor)
        self.CheckButton.grid(row=0,column=1, sticky=tk.E)
        self.bind(sequence="<Button-1>",func=self.toggle)


    def toggle(self, event):

        tkvar = self.variable
        if tkvar: tkvar.set(not tkvar.get())
        if self._command: self._command(event)

class LabelIcon(ttk.Labelframe):

    "Label widget with an mdi icon in a button in it."
    
    def __init__(self,  icon: mdiType, icon_size: int = 50, master = None, *, labelanchor = "w", cursor = "",
                command = "", style="noframe.TLabelframe", **kwargs):
        
        super().__init__(master, cursor=cursor, labelanchor=labelanchor, style=style, **kwargs)        
        
        self.columnconfigure(0,weight=1)
        self.columnconfigure(1,weight=1)
        self.columnconfigure(2,weight=1)

        b = self.cget("style")
        bootstyle = Bootstyle.ttkstyle_widget_color(b)
        if not bootstyle: bootstyle="primary"

        self._iconImg = MDIIcon(icon, (icon_size,icon_size), bootstyle=bootstyle)
        
        self._button = ttk.Button(self,image=self._iconImg, cursor=cursor, 
                        width=icon_size, padding=-1, style=f"image.TButton",
                        )
        
        self._button.grid(row=0,column=0, columnspan=3, sticky="nsew")
        if command:
            self.bind("<Button-1>",func=command)
            self._button.bind("<Button-1>",func=command)
        

class Treeview(ttk.Treeview):

    """Treeview with base styling and bindings for hovering.

    Usage is a bit complicated, since just using this as a subclass for some reason caused the Tree to stop opening items when clicking on the + (which also happens when setting up the tree in the __init__).
    So set up a Treeview first, and pass that. The class will function exactly the same as a normal treeview.
    """

    _treeframe: ttk.Frame = None

    def __init__(self, tree: ttk.Treeview, 
                on_select: Callable[["Treeview", tk.Event, tuple[iidType,]], None] = const.DEFAULT,
                on_hover: Callable[["Treeview", tk.Event, iidType], None] = const.DEFAULT,
                on_double_click: Callable[["Treeview", tk.Event, iidType], None] = const.DEFAULT):
        

        self.__tree_ph = tree

        tree.configure(style=const.TREEVIEW_STYLE, selectmode="browse")

        if tree.master != Treeview._treeframe:
            _LOGGER.verbose("Tree has the wrong master widget!")
            tree.master = Treeview._treeframe

        self.tooltip = ToolTip(self.tree, bootstyle=const.TOOLTIP_STYLE)
        self.last_hover: str = None
        "The last item hovered over in this tree"

        if on_select == const.DEFAULT: on_select = self.highlight_element
        if on_hover == const.DEFAULT: on_hover = None
        if on_double_click == const.DEFAULT: on_double_click = None

        self.__on_hover_function = None
        self.__on_select_function = on_select
        self.__on_double_click_function = None

        self._element_iids: dict[str,set] = {}
        #Holds all registered iid for a given element

        self._element_items : dict[str,"Element"] = {}
        #Maps iids to elements

        self.tooltip.move_tip()
        self.tooltip.hide_tip()

        self.tree.tag_configure(const.HOVER_TAG, background="grey")
        self.tree.bind("<Motion>", self._hover)
        self.tree.bind("<Leave>", self._leave)

        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<<TreeviewSelect>>", self.__on_select)
        self.tree.bind("<Double-1>", self.__on_double_click)


    def __getattr__(self, name):
        return getattr(self.tree, name)

    #region
    @property
    def tree(self) -> ttk.Treeview:
        "The actual treeview"
        return self.__tree_ph

    @property
    def on_hover(self) -> Callable[["Treeview", tk.Event, iidType], None]:
        """Function to call when a new item is hovered over (focused). 
        Useful to configure the text of the tooltip. Defaults to None."""
        return self.__on_hover_function

    @on_hover.setter
    def on_hover(self, value):
        if not isinstance(value, Callable):
            value = None
        self.__on_hover_function = value
        return
    
    @property
    def on_select(self) -> Callable[["Treeview", tk.Event, tuple[iidType,]], None]:
        """Function to call whenever an item is selected. 
        Does not directly pas an iid, but the tuple of selected iid's"""
        return self.__on_select_function
    
    @on_select.setter
    def on_select(self, value):
        if not isinstance(value, Callable):
            value = None
        self.__on_select_function = value

    @property
    def on_double_click(self) -> Callable[["Treeview", tk.Event, iidType], None]:
        "Function to call whenever an item is double clicked. Defaults to None"
        return self.__on_double_click_function
    
    @on_double_click.setter
    def on_double_click(self, value):
        if not isinstance(value, Callable):
            value = None
        self.__on_double_click_function = value
    #endregion

    def _hover(self, event):

        _iid = self.identify_row(event.y)
        if not _iid:
            if self.last_hover:
                self.item(self.last_hover, tags=[])
                self.last_hover = None
            self.tooltip.hide_tip()
            return
        
        if _iid != self.last_hover:
            _LOGGER.verbose(f"Hovered over iid {_iid}")
            if self.last_hover:
                self.tooltip.hide_tip()
                self.item(self.last_hover, tags=[])
            self.item(_iid, tags=[const.HOVER_TAG])
            self.last_hover = _iid
            self.__on_hover(event, _iid)

    def _leave(self, event):    
        self.tooltip.hide_tip()
        if self.last_hover:
            self.tooltip.hide_tip()
            self.item(self.last_hover, tags=[])
            self.last_hover = None
        return
    
    def _click(self, event: tk.Event):
        if not self.identify_row(event.y):
            for item in self.selection():
                self.selection_remove(item)

    def __on_select(self, event: tk.Event):
        if not self.on_select: return
        if not self.selection(): return
        return self.on_select(self, event, self.selection())

    def __on_hover(self, event, iid):
        "Settable, called when a new tree item is hovered over"
        if not self.on_hover: 
            return
        return self.on_hover(self, event, iid)
    
    def __on_double_click(self, event: tk.Event):
        "Settable, called when a new tree item is hovered over"
        if not self.on_double_click: 
            return
        iid = self.identify_row(event.y)
        if not iid: return
        return self.on_double_click(self, event, iid)    
    
    def state(self,statespec=None):
        if statespec:
            e = super().state(statespec)
            if 'disabled' in e:
                self.tree.bindtags(self.tags)
            elif '!disabled' in e:
                self.tags = self.tree.bindtags()
                self.tree.bindtags([None])
            return e
        else:
            return super().state()

    def disable(self):
        self.state(('disabled',))

    def enable(self):
        self.state(('!disabled',))

    def is_disabled(self):
        return 'disabled' in self.state()

    def is_enabled(self):
        return not self.is_disabled()
    
    def insert_element_item(self, element: "Element", text: str, parent_iid="", index=tk.END) -> str:
        """
        Shorthand function to add an item for an element to the tree, such that it can be used with the highlight function.

        Parameters
        ----------
        element : Element
            The element to build the tree item of
        text : str
            String to put as text in the item
        parent_iid : str, optional
            iid of the parent item, by default ""
        index : _type_, optional
            Index to insert into, by default tk.END

        Returns
        -------
        str
            iid of the new item
        """

        if element.id in self._element_iids:
            iid_idx = len(self._element_iids[element.id]) + 1
        else:
            self._element_iids[element.id] = set() ##Using sets to prevent any duplicates
            iid_idx = 0
        
        iid = f"{element.id}-iid_{iid_idx}"
        self._element_iids[element.id].add(iid)
        self._element_items[iid] = element

        item_iid = self.tree.insert(
            parent_iid,
            index=index,
            iid=iid,
            text=text,
            image=tk_functions.get_element_tree_icon(element)
            )
        return item_iid
    
    def highlight_element(self, tree, event, iid):
        
        iid = iid[0]
        if iid not in self._element_items:
            tk_functions.highlight_elements() ##Remove any present highlights
            return
        
        elt = self._element_items[iid]
        tk_functions.highlight_elements(elt)
        return

class CanvasBackground(PhotoIcon):
    "MDI_PIL PhotoIcon implementation to change the background image depending on theme type."

    def __init__(self, size, **kw):

        self._file_light = Path(__file__).parent.parent / "files" / "background_alpha_light.png"
        self._file_dark = Path(__file__).parent.parent / "files" / "background_alpha_dark.png"

        assert self._file_light.exists()

        image = self._create_images(size)

        super().__init__(image, size, **kw)

    def _create_images(self, size):
        self._image_light = ImageOps.pad(Image.open(self._file_light),
                                    size, centering=(1,1))
        self._image_dark = ImageOps.pad(Image.open(self._file_dark),
                                    size, centering=(1,1))
        style = ttk.Style.get_instance()
        self._current_type = style.theme.type
        if self._current_type == ttk.LIGHT:
            return self._image_light
        else:
            return self._image_dark

    def _change_img_style(self, *args):
        
        style = ttk.Style.get_instance()
        if style.theme.type == self._current_type:
            return
        
        img = self._img
        
        if style.theme.type == ttk.LIGHT:
            new_img = self._image_light
        else:
            new_img = self._image_dark

        new_img.putalpha(img.getchannel("A"))
        self.paste(new_img)
        self._current_type = style.theme.type

class PSSMCanvas(tk.Canvas):
    """tkinter Canvas widget that can be specialised for inkBoard designer.
    """
    master: "DesignerWindow"

    def __init__(self, master = None, **kwargs):
        
        self._background_Tk_idx = None
        super().__init__(master, **kwargs)
        
    def set_size(self, width: int, height: int):
        "Sets the size of the Canvas by correctly updating the size of the designer window."

        window_width = width + const.INTERFACE_WIDTH
        window_height = height

        self.master.geometry(f"{window_width}x{window_height}")
        self.master.update()
        self.master.update_idletasks()
        self._build_canvas_background()

    
    def _build_canvas_background(self):

        size = (self.winfo_width(),
                self.winfo_height())
        self._background_Tk = CanvasBackground(size)

        if self._background_Tk_idx:
            self.itemconfig(self._background_Tk_idx, image =  self._background_Tk)
        else:
            self._background_Tk_idx = self.create_image(0,0, anchor=tk.NW, image=self._background_Tk)
        self.update()
        return

    def _clear(self):
        "Clears the screen canvas from everything except the background"
        for idx in self.find_all():
            if idx == self._background_Tk_idx: 
                continue
            ##May need to check if this would cause issues with the rectangles, as it would obviously create a mismatch between them
            self.delete(idx)
        self.unbind("<Button>")
        self._build_canvas_background()
        self.update()



class BatteryFrame(ttk.Labelframe):
    "Frame to configure emulator battery settings"

    def __init__(self, master, device: "Device", **kwargs):

        super().__init__(master, text="Battery Settings",  
                        bootstyle=const.FEATURE_FRAME_STYLE, **kwargs)

        self._device = device

        frame = ttk.Frame(self)
        frame.grid(column=0, row=0, sticky="nsew",pady=(10,10))

        var = tk.BooleanVar(self,name="device.battery_rnd", value=device.battery._randomise)
        toggleFrame = LabelToggle(frame, text="Randomise", variable=var, command=self.__toggle_rnd)
        toggleFrame.grid(row=1, column=0, sticky="nsew", pady=(10,0))
        ToolTip(toggleFrame, "Return a random battery value and state each time the value is requested.",  bootstyle=const.TOOLTIP_STYLE)
        
        stateVar = ttk.StringVar(master=self, name="battery.state")    
        stateVar.trace_add("write",self.__set_state)

        ops = ["full","charging","discharging"]
        stateFrame = ttk.Labelframe(frame,text="State", style='toggleCenter.TLabelframe', labelanchor="n")
        stateBox = ttk.Combobox(stateFrame, textvariable=stateVar, values=ops, state="readonly", width=25, cursor="hand2")
        
        stateBox.grid(row=0,column=0)
        stateFrame.grid(row=0,column=0)


        digit_func = device.window.register(self.__validate_charge)
        chargevar = ttk.IntVar(self, device.battery.charge, "battery.charge")
        chargevar.trace_add("write",self.__set_charge_var)
        trFrame = ttk.Labelframe(frame,text="Charge", style='toggleCenter.TLabelframe', labelanchor="n")
        trFrame.columnconfigure(0,weight=1)
        chargeBox = ttk.Spinbox(trFrame, from_=0, to=100, command=self.__set_charge, 
                                    validate="key", validatecommand=(digit_func, '%P', "%W"))
        chargeBox.grid(row=0,column=0, sticky="ew")
        trFrame.grid(row=0, column=1)

        button = ttk.Button(frame, command=self.__call_update, text="Update Now", style="primary")
        button.grid(row=1, column=1)
        ToolTip(button,)

        self.chargevar = chargevar
        self.chargeBox = chargeBox
        self.stateVar = stateVar

        chargeBox.set(chargevar.get())
        stateBox.set(self._device.battery.state)

    def __toggle_rnd(self, *args):
        val = self.getvar("device.battery_rnd")
        
        self._device.battery._randomise = bool(val)

    def __validate_charge(self, value, widget_name):
        try:
            value = int(value)
        except ValueError:
            return False
            
        w = self.nametowidget(widget_name)

        if value >= 0 or value <= 100:
            w.set(value)
            ##This retrieves the actual command attached to the widget
            cmd = lambda : self.tk.call(w['command'])
            cmd()
            return True
        else:
            return False
        
    def __set_state(self, *args):

        val = self.stateVar.get()

        if val == "full" and self._device.battery.charge != 100:
            _LOGGER.warning("Battery only reports full at 100%, change the charge first")
        self._device.battery._set_state(val)

    def __set_charge_var(self, var_name, *args):
        val = self.chargevar.get()
        self._device.battery._set_charge(val)
        return

    def __set_charge(self, *args):
        val = self.chargeBox.getint(self.chargeBox.get())
        self._device.battery._set_charge(val)
        return

    def __call_update(self, *args):
        async def notify_condition():
            condition = self._device.parentPSSMScreen.deviceUpdateCondition
            async with condition:
                condition.notify_all()

        asyncio.create_task(notify_condition())


class BacklightFrame(ttk.Labelframe):
    "Frame to configure emulator backlight settings"

    def __init__(self, master, device: "Device", **kwargs):

        self._device = device

        super().__init__(master, text="Backlight Settings",  
                        bootstyle=const.FEATURE_FRAME_STYLE, **kwargs)

        frame = ttk.Frame(self)
        frame.grid(column=0, row=0, sticky="nsew")

        num_cols = 5
        slider_pad = (5,5)

        self.simulate_var = tk.BooleanVar(device.window, name="backlight.simulate")
        toggleFrame = LabelToggle(master=frame, labelanchor=tk.N, text="Simulate", variable=self.simulate_var, command=self.__toggle_backlight)
        toggleFrame.grid(row=0, column=num_cols-1, sticky="nsew")
        ToolTip(toggleFrame, "Place a semi-transparent dark rectangle over the screen, to simulate the backlight. Rectangle becomes more transparent when brightness goes up.",  bootstyle=const.TOOLTIP_STYLE)

        val = device.Screen.backlight_behaviour.title()
        self.backlightBehv = ttk.StringVar(master=device.window, name="backlight.behaviour")
        self.backlightBehv.trace_add("write",self.__set_behaviour)
                
        ops = ["Manual", "On Interact", "Always"]
        behvlabel = ttk.Label(frame, text="Behaviour", anchor=tk.W)
        behv = ttk.Combobox(frame, textvariable=self.backlightBehv, values=ops, state="readonly", width=25, cursor="hand2")
        behv.set(val)
        behvlabel.grid(row=0, column=0, sticky=tk.W)
        behv.grid(row=0, column=1, columnspan=num_cols-2)
        ToolTip(behvlabel,"Backlight behaviour. Manual means it only turns on/off when called explicitly. On Interact means it turns on when interacting with the screen. Always means it is always on by default (can be turned on/off via functions). Initial behaviour is set in configuration.yaml", bootstyle=const.TOOLTIP_STYLE)


        brtLabel = ttk.Label(frame, text="Brightness", anchor=tk.W)
        var = tk.IntVar(self, name="backlight.brightness", value=device.backlight.brightness)
        brtSlide = ttk.Scale(frame, command=self.__set_brightness, name="brightness",  from_=0, to=100, length=None, cursor="hand2", variable=var)
        brtSlide.grid(row=1,column=1, sticky=tk.EW, columnspan=num_cols-1, pady=slider_pad)
        brtLabel.grid(row=1, column=0, sticky=tk.EW, padx=(0,10))
        brtSlide.bind('<Button-1>', tk_functions.set_slider_left_click)


        defbrtLabel = ttk.Label(frame, text="Default Brightness", anchor=tk.W)
        defbrtSlide = ttk.Scale(frame, command=self.__set_default_brightness, name="default_brightness",  from_=0, to=100, length=None, cursor="hand2")
        defbrtSlide.grid(row=2,column=1, sticky=tk.EW,  columnspan=num_cols-1, pady=slider_pad)
        defbrtLabel.grid(row=2, column=0, sticky=tk.EW, padx=(0,10))
        defbrtSlide.bind('<Button-1>', tk_functions.set_slider_left_click)
        ToolTip(defbrtLabel, "The default brightness (0-100) when turning on the backlight without specifying a brightness.", bootstyle=const.TOOLTIP_STYLE)

        ##Spinboxes
        spFrame = ttk.Frame(frame)
        spFrame.grid(row=3, columnspan=num_cols)
        digit_func = window.register(tk_functions.validate_positive_number)

        ##Default transition time
        trFrame = ttk.Labelframe(spFrame,text="Transition Time", style='toggleCenter.TLabelframe', labelanchor="n")
        trFrame.columnconfigure(0,weight=1)
        self.trBox = ttk.Spinbox(trFrame, command=self.__set_default_transition , validate="all", validatecommand=(digit_func, '%P', "%W"),
                                from_=0.0, to=60*60, increment=1) ##Somehow increments smaller than one mess up the widget so I guess it'll be like this.  
        self.trBox.set(device.backlight.defaultTransition)
        self.trBox.grid(row=0,column=0, sticky="ew")
        trFrame.grid(row=0, column=0)
        ToolTip(trFrame, "The default transition time (in seconds) when turning on/off the backlight without specifying a transition.", bootstyle=const.TOOLTIP_STYLE)
    
        offFrame = ttk.Labelframe(spFrame,text="Default on time", style='toggleCenter.TLabelframe', labelanchor="n")
        offFrame.columnconfigure(0,weight=1)
        self.offBox = ttk.Spinbox(offFrame, from_=0.0, to=60*60, command=self.__set_turn_off_time ,validate="key", validatecommand=(digit_func, '%P', "%W"))
        self.offBox.set(device.parentPSSMScreen.backlight_time_on)
        self.offBox.grid(row=0,column=0, sticky="ew")
        offFrame.grid(row=0, column=1)
        ToolTip(offFrame, "The default time the backlight stays on for (in seconds) when calling the screen's temporary backlight function without specifying a time.", bootstyle=const.TOOLTIP_STYLE)


    def __set_behaviour(self, *args):
        n = self.backlightBehv.get()
        self._device.Screen.set_backlight_behaviour(n)

    def __set_brightness(self, val):
        val = float(val)
        self._device.backlight.turn_on(int(val), transition=0)

    def __set_default_brightness(self, event: tk.Event):
        val = float(event)
        self._device.backlight.defaultBrightness = int(val)

    def __toggle_backlight(self, *args):
        var_name = "backlight.simulate"
        val = self.getvar(var_name)
        self._device.backlight.toggle_simulate(val)
        return

    def __set_default_transition(self,*args):
        val = self.trBox.get()
        self._device.backlight.defaultTransition = float(val)
        return

    def __set_turn_off_time(self,*args):
        val = self.offBox.get()
        self._device.parentPSSMScreen.backlight_time_on = float(val)



