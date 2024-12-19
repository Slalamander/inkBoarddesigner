
import logging
from typing import Literal
from math import floor
import tkinter as tk


import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip

from mdi_pil.ttkbootstrap_mdi import MDIIcon, MDIButton

from .. import const
from ..settings import EM_SETTINGS

from . import window
from .windows import DesignerWindow, TreeFrame
from .widgets import LabelToggle, LabelIcon, Treeview
from . import functions as tk_functions

logger = logging.getLogger(__name__)

_KEEP = []


def build_tk_button(root: tk.Tk, button_size : tuple[Literal["w"],Literal["h"]], icon : str, text : str, command=None, widget_name:str = None) -> tk.Button:
    """
    Builds a button for the tk window using the default values. Returns the button and image source (since that needs to be saved somewhere too.)
    Also makes the image to put upon it in the correct font.
    args:
        root: tk instance
        button_size: size of the button as a (w,h) tuple
        icon: mdi icon string
        text: text to show on the button
        command: optional command to call when the button is clicked
    """
    
    textSize = const.BUTTON_FONT_SIZE
    iconSize = int(textSize*1.5)

    imgTk = MDIButton(icon, text,button_size,const.HA_FONT_FILE,
                        iconSize,textSize, icon_margin=(0,3)
                    )
    _KEEP.append(imgTk)

    button = ttk.Button(root,image=imgTk,command=command, cursor=const.INTERACT_CURSOR, style=const.BUTTON_STYLE, padding=0,
                        takefocus=False, name=widget_name)
    return button

def build_interface_buttons(interface_frame: ttk.Frame):
    "builds the buttons used to run various designer functions"

    buttFrame = ttk.Frame(interface_frame)
    buttFrame.grid(row=0, column=0, pady=5, sticky=tk.NSEW)

    labelFrame = ttk.Frame(buttFrame)
    labelFrame.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW, padx=const.SETTINGS_PADDING)

    baselabel = ttk.Label(labelFrame, text="inkBoard", cursor="",
            font=const.DEFAULT_LABEL_FONT, anchor=tk.W,
            style="primary.TLabel")
    baselabel.pack(side=tk.LEFT)

    label = ttk.Label(labelFrame, text="Config", cursor="",
                    font=const.DEFAULT_LABEL_FONT, anchor=tk.W, 
                    bootstyle=(ttk.PRIMARY),  style="TLabel")
    label.bind("<Button-1>", tk_functions.open_config_folder)
    ToolTip(label, const.CONFIG_LABEL_TIP, bootstyle=const.TOOLTIP_STYLE)

    open_icon = MDIIcon("mdi:folder-open", (15,15))
    _KEEP.append(open_icon)

    open_button = ttk.Button(labelFrame,image=open_icon, 
                            style='image.TButton', 
                            cursor=const.INTERACT_CURSOR, command=tk_functions.open_new_config)
    ToolTip(open_button,const.CONFIG_OPEN_TIP, bootstyle=const.TOOLTIP_STYLE)
    
    open_button.pack(side=tk.RIGHT)

    window._buttonFrame = buttFrame
    window._buttonLabel = baselabel
    window._configLabel = label

    screenshotButton = build_tk_button(buttFrame,
                                    (const.BUTTON_WIDTH,const.BUTTON_HEIGHT),const.SCREENSHOT_BUTTON_ICON,const.SCREENSHOT_BUTTON_TEXT, 
                                    command=tk_functions.make_screenshot, widget_name=const.SCREENSHOT_BUTTON_NAME)
    screenshotButton.grid(column=0, row=1, 
                        sticky=tk.NW,padx=const.SETTINGS_PADDING)
    ToolTip(screenshotButton,const.SCREENSHOT_TIP, bootstyle=const.TOOLTIP_STYLE)

    packButton = build_tk_button(buttFrame,(const.BUTTON_WIDTH,const.BUTTON_HEIGHT),
                                const.PACK_BUTTON_ICON,const.PACK_BUTTON_TEXT, 
                                command=tk_functions.make_package, widget_name=const.PACK_BUTTON_NAME)
    packButton.grid(column=0, row=2, 
                    sticky=tk.NW, padx=const.SETTINGS_PADDING)
    ToolTip(packButton,const.PACK_TIP, bootstyle=const.TOOLTIP_STYLE)

    reloadButton = build_tk_button(buttFrame,(const.BUTTON_WIDTH,const.BUTTON_HEIGHT),
                                        const.RELOAD_BUTTON_ICON,const.RELOAD_BUTTON_TEXT, 
                                        command=tk_functions.reload_config, widget_name=const.RELOAD_BUTTON_NAME)
    reloadButton.grid(column=1, row=1, 
                    sticky=tk.NE, padx=(0,const.SETTINGS_PADDING))
    ToolTip(reloadButton,const.RELOAD_TIP, bootstyle=const.TOOLTIP_STYLE)

    quitButton = build_tk_button(buttFrame,(const.BUTTON_WIDTH,const.BUTTON_HEIGHT),
                                        const.STOP_BUTTON_ICON, const.STOP_BUTTON_TEXT, 
                                        tk_functions.stop_emulator, const.STOP_BUTTON_NAME)
    quitButton.grid(column=1, row=2, 
                    sticky=tk.NE, padx=(0,const.SETTINGS_PADDING))
    ToolTip(quitButton,const.STOP_TIP, bootstyle=const.TOOLTIP_STYLE)

    window.interface_buttons = (screenshotButton, packButton, reloadButton, quitButton)


def build_label_fill(root, size : tuple[Literal["w"],Literal["h"]], text:str, tiptext:str, var : tuple[tk.Variable,"function"]=(None,None), command=None):
    w,h = size

    frame = LabelToggle(root,text=text,
                        width=w,height=h,
                        style='noframe.TLabelframe', 
                        labelanchor="w", padding=10, cursor=const.INTERACT_CURSOR)
    ToolTip(frame, text=tiptext,bootstyle=const.TOOLTIP_STYLE)
    return frame

def build_label_toggle(root, size : tuple[Literal["w"],Literal["h"]], text:str, tiptext:str, var: tk.Variable = None, command=None):
    "Builds toggle buttons with labels and a tooltip"
    w,h = size
    frame = LabelToggle(root,text=text,
                        width=w,height=h, variable=var, command=command,
                        labelanchor="w", padding=10, cursor=const.INTERACT_CURSOR)
    ToolTip(frame, text=tiptext,bootstyle=const.TOOLTIP_STYLE)
    return frame

def build_label_icon(root,size : tuple[Literal["w"],Literal["h"]], text:str, tiptext:str, var : tuple[tk.Variable,"function"]=(None,None), command=""):
    w,h = size
    icon = "mdi:cog"
    icon_size = int(h*0.75)
    frame = LabelIcon(icon, icon_size, text=text,
                    master=root, width=w,height=h,padding=10, cursor=const.INTERACT_CURSOR, command=command)
    ToolTip(frame, text=tiptext,bootstyle=const.TOOLTIP_STYLE)

    return frame

def build_settings_frame(interface_frame: ttk.Frame):
    "Builds the frames that holds the settable option widgets"

    settFrame = ttk.Labelframe(interface_frame, text="Settings",
                            bootstyle=ttk.PRIMARY,
                            padding=0)
    settFrame.grid(column=0, row=1, sticky="nsew", padx=0, pady=(5,0))

    window._settingsFrame = settFrame

    dmVar = window.darkmode_variable
    dmFrame = build_label_toggle(settFrame,(const.SETTINGS_WIDTH, int(const.SETTINGS_HEIGHT/2)),
                                        text="Dark Mode", tiptext=const.DARKMODE_TIP,command=tk_functions.change_theme, var=dmVar)
    dmFrame.grid(row=0,column=0, sticky="e",padx=const.SETTINGS_PADDING)

    saveVar = window.saveas_variable
    saveFrame = build_label_toggle(settFrame,(const.SETTINGS_WIDTH, int(const.SETTINGS_HEIGHT/2)), 
                        text="Save As", tiptext=const.SAVEAS_TIP, var=saveVar)
    saveFrame.grid(row=2,column=0, sticky="e",padx=const.SETTINGS_PADDING)

    hlVar = window.hightlight_variable
    hlFrame = build_label_toggle(settFrame,(const.SETTINGS_WIDTH, int(const.SETTINGS_HEIGHT/2)), 
                        text="Highlight", tiptext=const.HIGHLIGHT_TIP, var=hlVar)
    hlFrame.grid(row=1,column=0, sticky="e",padx=const.SETTINGS_PADDING)

    blVar = tk.BooleanVar(window, value=EM_SETTINGS.getboolean("backlight"), name="backlight")
    blFrame = build_label_icon(settFrame,(const.SETTINGS_WIDTH, int(const.SETTINGS_HEIGHT/2)), 
                        text="Config", tiptext=const.CONFIG_OPTIONS_TIP, command=tk_functions.open_config_window)
    blFrame.grid(row=0,column=1, sticky="e",padx=const.SETTINGS_PADDING)
    
    deviceFrame = build_label_icon(settFrame,(const.SETTINGS_WIDTH, int(const.SETTINGS_HEIGHT/2)), 
                        text="Device", tiptext=const.DEVICE_TIP, command=tk_functions.open_device_window)
    deviceFrame.grid(row=1,column=1, sticky="e",padx=const.SETTINGS_PADDING)

    listFrame = ttk.Labelframe(settFrame,text="List",
                            height=int(const.SETTINGS_HEIGHT/2), style='noframe.TLabelframe', labelanchor="w")
    listFrame.grid(row=3,column=0, columnspan=2, sticky="ns", pady=0, padx=const.SETTINGS_PADDING)

    listFrame.grid_columnconfigure(0, weight=7)
    listFrame.grid_columnconfigure(1, weight=3)

    menu = ttk.Combobox(listFrame, state="readonly", values = const.DEFAULT_LIST_OPTIONS, 
                        width=const.LIST_WIDTH, textvariable=window._tree_list_variable)
    window._list_menu = menu

    menu.grid(row=0, column=0, sticky="NSEW")

    icon_size = int((const.SETTINGS_HEIGHT/2)*0.6)
    imgTk = MDIIcon("mdi:refresh", (icon_size,icon_size))
    _KEEP.append(imgTk)

    button = ttk.Button(listFrame, image=imgTk, cursor="hand2", padding=int(icon_size/4), style="image.TButton")
    ToolTip(button,const.TREE_REFRESH_TIP, bootstyle=const.TOOLTIP_STYLE)
    button.grid(row=0,column=1, sticky="nsew")

def build_tree_frame(frame: ttk.Frame):

    treeFrame = TreeFrame(frame, padding=0, name=const.TREE_FRAME_NAME)
    treeFrame.pack(anchor=tk.S, fill=tk.BOTH, expand=1, ipady=10)

    treeFrame._window = window
    window._treeFrame = treeFrame

    element_treeview = Treeview(ttk.Treeview(columns=("entity"),))
    element_treeview.heading("#0", text="Element", anchor="w")
    element_treeview.column("#0", width= floor(const.INTERFACE_WIDTH*0.375)) ##Width and height are empty
    element_treeview.heading("entity", text="Entity", anchor="w")
    element_treeview.column("entity", width= floor(const.INTERFACE_WIDTH*0.475))
    
    treeFrame._base_trees[const.ELEMENT_TREE_OPTION.lower()] = element_treeview
    treeFrame._element_tree = element_treeview
    return


def build_interface():
    "Builds the button interface for the designer"

    ui_frame = ttk.Frame(window, name=const.UI_FRAME_NAME,
                            width=const.INTERFACE_WIDTH-2*const.INTERFACE_BORDER, borderwidth=const.INTERFACE_BORDER,
                            style='right.TFrame', 
                            )

    iface_frame = ttk.Frame(ui_frame,
                            style='buttons.TFrame')
    iface_frame.pack()

    build_interface_buttons(iface_frame)
    build_settings_frame(iface_frame)
    build_tree_frame(ui_frame)
    return ui_frame


def create_canvas(size: tuple[int,int]):
    "Creates the canvas widget that the pssm screen will print on"

    canvas = window.setup_canvas(size)    
    return canvas

def build_window() -> DesignerWindow:

    title = "inkBoard Designer"
    window.wm_title(title)
    
    init_width = const.INTERFACE_WIDTH*4
    init_height = int((init_width*9)/16)

    window.geometry(f"{init_width}x{init_height}")
    window.focus_force()

    iface = build_interface()
    window.setup_canvas((init_width-const.INTERFACE_WIDTH, init_height))

    iface.place(anchor=tk.NE,width=const.INTERFACE_WIDTH,relx=1,rely=0, relheight=1)
    return window

