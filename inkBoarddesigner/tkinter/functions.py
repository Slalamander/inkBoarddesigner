import logging
from pathlib import Path
from typing import *
from datetime import datetime as dt
import webbrowser
import tkinter as tk


from contextlib import suppress
from tkinter.filedialog import asksaveasfile, askopenfile

import ttkbootstrap as ttk
from ttkbootstrap import colorutils, style as ttk_style
from mdi_pil import ttkbootstrap_mdi as ttk_mdi

from PIL import Image, ImageTk, ImageOps

from inkBoard import core as CORE, packaging
from inkBoard.helpers import QuitInkboard
##Suspect this one won't work here.
##Seems to at least with quit? Check with screenshot too though.

from .. import const
from ..const import THEME_DARK, THEME_LIGHT
from ..settings import EM_SETTINGS

if TYPE_CHECKING:
    from .widgets import DesignerWindow
    from PythonScreenStackManager.elements import Element

    from . import windows, widgets
    from .. import runners

window: "DesignerWindow"

_LOGGER = logging.getLogger(__name__)

def configure_themes(themes : tuple = (THEME_DARK, THEME_LIGHT)):
    "Configures the passed themes to use with inkBoard. Last passed theme will be the one used at startup."

    ibHex = const.INKBOARD_COLORS["inkboard"]
    ibHex = colorutils.color_to_hex(ibHex[:3])
    ibHex_light = const.INKBOARD_COLORS["inkboard-light"]
    ibHex_light = colorutils.color_to_hex(ibHex_light[:3])

    ibHex_grey = const.INKBOARD_COLORS["inkboard-gray"]
    ibHex_grey = colorutils.color_to_hex(ibHex_grey[:3])
    
    for theme in themes:
        style = ttk.Style(theme=theme)
        style.colors.set("dark", ibHex)
        if theme == THEME_LIGHT:
            style.colors.set("primary", ibHex)
            bghsl = colorutils.color_to_hsl(color=style.colors.bg, model="hex")
            newl = min( int(bghsl[-1]*0.85), 100)
                            
            buttonbg = colorutils.update_hsl_value(color=bghsl,lum=newl, inmodel="hsl", outmodel="hex")
            newl = min( int(newl*1.111), 100)
            buttonAct = colorutils.update_hsl_value(color=bghsl,lum=newl, inmodel="hsl", outmodel="hex")
        elif theme == THEME_DARK:
            style.colors.set("primary", ibHex_light)
            bghsl = colorutils.color_to_hsl(color=style.colors.bg, model="hex")
            newl = min( int(bghsl[-1]*1.5), 100)
            
            buttonbg = colorutils.update_hsl_value(color=bghsl,lum=newl, inmodel="hsl", outmodel="hex")
            newl = min( int(newl*0.9), 100)
            buttonAct = colorutils.update_hsl_value(color=bghsl,lum=newl, inmodel="hsl", outmodel="hex")
            
            ##Putting this outside the dark theme config somehow messes up the generation (since the bars etc. are images made with PIL)
            ##So keep this in here for the correct scrollbar style
            bg = style.colors.bg
            style.configure(const.SCROLLBAR_STYLE, 
                            relief="flat",
                            lightcolor=bg, darkcolor=bg,
                            troughcolor=bg, bordercolor=bg,
                            background=bg,
                            arrowsize=11)
            s = style.configure(const.SCROLLBAR_STYLE)
            style.colors.set("dark", ibHex)

        style.colors.set("secondary", buttonbg)
        style.configure('main.TFrame', relief='flat', background=style.colors.bg)

        ##Relief must be flat otherwise there's a white border on the border
        style.configure('right.TFrame', relief='flat', background=ibHex)
        style.configure('buttons.TFrame', relief='flat', background=style.colors.bg)

        ##ttk treeviews seem to not have header borders so will use reliefs
        style.layout('Treeview', 
            [('Treeview.field', {'sticky': 'nswe', 'children': [
                ('custom.Treeview.padding', {'sticky': 'nswe', 'children': [
                    ('custom.Treeview.treearea', {'sticky': 'nswe'})
                    ]})
                ]})
            ])   

        style.configure(f'{const.TREEVIEW_STYLE}.Heading', font=('Arial Bold', 10),                 
            foreground=style.colors.primary,
            background=buttonAct,
            bordercolor=buttonbg,
            darkcolor=buttonAct,
            lightcolor=buttonAct,
            borderwidth=0,
            relief='raised')

        style.map(const.TREEVIEW_STYLE,
            fieldbackground=[('!disabled',style.colors.bg), ('!selected',style.colors.bg)],
            bordercolor=[('!disabled',style.colors.bg),('!selected',style.colors.bg)],
            borderwidth=[('!disabled',0),('!selected',0)])

        style.configure(const.TREEVIEW_STYLE, 
                        borderwidth=0, padding=0, indent=5, background=style.colors.bg
                        )

        style.configure(const.BUTTON_STYLE, borderwidth=10, bordercolor=style.colors.bg,
                        background=buttonbg, relief="solid", shiftrelief=3, 
                        foreground="black")
        
        style.map(const.BUTTON_STYLE, background=[('pressed',buttonAct),('active', buttonAct)],
            relief=[('pressed','sunken'),("!pressed", "solid")],
            highlightthickness = [('pressed',0)]
            )
        
        style.configure("image.TButton", borderwidth=0, bordercolor=style.colors.bg, background=style.colors.bg)
        style.map('image.TButton', 
            background=[('pressed',buttonAct),('active', style.colors.bg)],
            relief=[('pressed','sunken'),("!pressed", "solid"), ]
            )

        style.configure("TLabel",background=style.colors.bg,)
        style.configure(const.LOADBAR_LABEL_STYLE, background=style.colors.secondary,)
        for kw in ttk_style.Keywords.COLORS:
            style.configure(f'{kw}.{const.LOADBAR_LABEL_STYLE}', 
                            background=style.colors.secondary, foreground=getattr(style.colors, kw))
            style.configure(f"{kw}.TLabel", foreground=getattr(style.colors, kw))


        style.configure('noframe.TLabelframe', labeloutside=False, padding=(2,10))
        style.configure('noframe.TLabelframe.Label',  foreground=style.colors.primary)
        style.configure('toggleCenter.TLabelframe', labeloutside=False)
        style.configure('toggleCenter.TLabelframe.Label',  foreground=style.colors.primary)

        style.configure("primary.TLabelframe", padding=(2,0), bordercolor=style.colors.bg)
        style.configure("primary.TLabelframe.Label",font=('Arial Bold', 10), foreground=style.colors.primary)
        
        style.configure("secondary.TLabelframe", padding=(2,0), bordercolor=style.colors.bg)
        style.configure("secondary.TLabelframe.Label",font=('Arial Bold', 10), foreground=style.colors.secondary)

    return
        

def change_theme(*args):
    "Changes the theme based on the value of the darkmode variable"
    newVal = window.globalgetvar(const.DARKMODE_VAR_NAME)
    if newVal:
        _LOGGER.verbose("Turning on dark mode")
        new = THEME_DARK
    else:
        _LOGGER.verbose("Turning off dark mode")
        new = THEME_LIGHT

    window.style.theme_use(new)
    window.trace_variable(const.DARKMODE_VAR_NAME)

_BG_IMG_TK = []
def build_canvas_background(size: tuple[int,int]):
    "(re)builds the background for the designer"

    if _BG_IMG_TK:
        _BG_IMG_TK.clear()

    img_file = Path(__file__).parent.parent / "files" / "background_alpha.png"
    bgImg = Image.open(img_file)
    bgImg = ImageOps.pad(bgImg,size, centering=(1, 1)) #Centering here should align the image to the right, and vertically centered
    bgTk = ImageTk.PhotoImage(bgImg)
    _BG_IMG_TK.append(bgTk)
    return bgTk

def make_screenshot():
    "Makes a screenshot of the current dashboard view."
    if not hasattr(CORE.screen.device,"last_printed_PIL"):
        return
    
    img: Image.Image = CORE.screen.device.last_printed_PIL.copy()
    save_image(img)

def save_image(img: Image.Image, base_name: str = "Inkboard_Screenshot_"):
    """
    Saves an image instance, opens the save_as window depending on the setting

    Parameters
    ----------
    img : Image.Image
        The image to save
    base_name : str, optional
        Base name to use for the filename, by default "Inkboard_Screenshot_"
    """    

    date = dt.now().strftime("%Y_%m_%d_%H%M%S")
    filename = str(base_name) + date
    folder = CORE.config.baseFolder / "screenshots"
    if EM_SETTINGS.getboolean(const.SAVEAS_VAR_NAME,True):
        
        if not Path(folder).exists():
            folder.mkdir()

        _LOGGER.debug("Opening save as dialog")
        files = [('PNG', '*.png'), 
            ('JPEG', '*.jpg'),
            ("BMP", "*.bmp"),
            ('All Files', '*.*')] 
        file = asksaveasfile(filetypes = files, defaultextension = files,
                            initialdir=folder, initialfile=filename)
        if file == None:
            return
        filename = file.name
    else:
        
        if not folder.exists():
            folder.mkdir()
        filename = folder / f"{filename}.png"
    
    img.save(filename)
    _LOGGER.info(f"Screenshot saved as {filename}")

def make_package(*args):
    ##Will extend this later to include dealing saveas screens etc.
    packaging.create_core_package(CORE, pack_all=True)


def open_device_window(event):
    
    ##This maybe does not make much sense?
    device = getattr(CORE,"device",None)

    windows.DeviceWindow(device)
    return

def open_config_window(event):
    windows.ConfigWindow(CORE)
    return


def set_slider_left_click(event : tk.Event):
    """Sets a sliders position when left clicking by simulating a right click. Bind this function to a sliders left click to do so."""
    widg = event.widget
    widg.event_generate('<Button-3>', x=event.x, y=event.y)
    return

def reload_config(*args):
    #Starts the reload process
    if window._inkBoard_thread.is_alive() and hasattr(CORE,"screen"):
        CORE.screen.reload()
    elif window._current_config_file:
        window._mainLoop.create_task(
            runners.reload_config(window._current_config_file))
    else:
        _LOGGER.warning("No config is currently loaded")


def stop_emulator(*args, exce=None, new_state=None):
    try:
        window.set_inkboard_state(new_state)

        if new_state == None:
            window.update()
    except tk.TclError:
        pass

    if not window._inkBoard_thread.is_alive():
        return

    if exce == None:
        exce = QuitInkboard("Quitting Emulator")

    if hasattr(CORE,"screen") and CORE.screen.printing:
        CORE.screen.quit(exce)

    return


MDI_TREE_ICONS = {}
def build_tree_icon(icon: str) -> ttk_mdi.MDIIcon:
    """
    Builds an icon widget for the element tree, or returns it if it already exists

    Parameters
    ----------
    icon : str
        mdi icon to make an icon off

    Returns
    -------
    ttk_mdi.MDIIcon
        The icon widget
    """    
    if icon in MDI_TREE_ICONS:
        return MDI_TREE_ICONS[icon]
    
    mdi_icon = icon
    icon = ttk_mdi.MDIIcon(icon, const.TREEVIEW_ICON_SIZE)
    MDI_TREE_ICONS[mdi_icon] = icon
    return icon

def get_tree_icon(icon: ttk_mdi.mdiType):
    """Gets the icon widget corresponding to the provided mdi icon. If it does not exist, it is made.

    Parameters
    ----------
    icon : ttk_mdi.mdiType
        mdi icon to get the icon of

    Returns
    -------
    ImageTk.PhotoImage
        The object to be used as a treeview item's image argument
    """    
    return build_tree_icon(icon)

def validate_positive_number(value: str, widget_name: str):
    try:
        value = value.lstrip().replace(",",".")
        value = float(value)
    except ValueError:
        return False
        
    w = window.nametowidget(widget_name)

    if value >= 0:
        w.set(str(value))
        ##This retrieves the actual command attached to the widget
        cmd = lambda : window.tk.call(w['command'])
        cmd()
        return True
    else:
        return False

ELEMENT_ICONS_MDI = {"default": const.DEFAULT_ELEMENT_ICON}
ELEMENT_ICONS_TK = {}

def get_element_tree_icon(element: "Element"):
    
    if "default" not in ELEMENT_ICONS_TK:
        ELEMENT_ICONS_TK["default"] = build_tree_icon(ELEMENT_ICONS_MDI["default"])

    elt_class = str(element.__class__.__name__)
    elt_icon = element._emulator_icon
    if ELEMENT_ICONS_MDI.get(elt_class,"not present") != elt_icon:
        icon = build_tree_icon(elt_icon)
        ELEMENT_ICONS_MDI[elt_class] = elt_icon
        ELEMENT_ICONS_TK[elt_class] = icon
        return icon
    
    return ELEMENT_ICONS_TK.get(elt_class,ELEMENT_ICONS_TK["default"])

##Move highlight function to here.
_INDICATOR_RECTANGLES = []
def highlight_elements(*element_list : "Element"):
    "Pass items to draw a square around. Removes currently drawn squares first."
    _LOGGER.verbose(f"Removing {len(_INDICATOR_RECTANGLES)} rectangles.")
    for rect in _INDICATOR_RECTANGLES:
        ##If this throws errors after clearing: either use find_above and just delete them from there
        ##Just need to know the tag of the screen image itself.
        window.screenCanvas.delete(rect)

    _INDICATOR_RECTANGLES.clear()

    if not EM_SETTINGS.getboolean(const.HIGHLIGHT_VAR_NAME):
        return

    for elt in element_list:
        _LOGGER.debug(f"Selected element in area {elt.area}")
        if elt.area == None or not elt.onScreen:
            continue
        [(x,y),(w,h)] = elt.area
        rect = window.screenCanvas.create_rectangle(x,y,x+w,y+h, outline=const.HIGHLIGHT_COLOR,
                                    dash=const.HIGHLIGHT_DASH, width=const.HIGHLIGHT_WIDTH)
        _INDICATOR_RECTANGLES.append(rect)    

def open_config_folder(*args):
    with suppress(AttributeError):  #Suppressing in case it's called too early e.g.
        folder = CORE.config.baseFolder ##Better to use the folder, using the file seemed to open it in vscode
        webbrowser.open("file:///" + str(folder))
    

    ##Current solution (using webbrowerser) found here: https://stackoverflow.com/a/54641180
    ##Should work regardless of platform?
    ##Otherwise, try e.g. this package: https://pypi.org/project/show-in-file-manager/

    return

def open_new_config(*args):
    
    if hasattr(CORE,"config"):
        init_folder = CORE.config.baseFolder
    elif window._current_config_file:
        init_folder = Path(window._current_config_file).parent.absolute()
    else:
        init_folder = Path.cwd()

    _LOGGER.debug("Opening save as dialog")
    files = [('YAML', '.yaml .yml'),
        ('All Files', '*.*')] 
    file_obj = askopenfile(filetypes = files, defaultextension = files,
                        initialdir=init_folder, )
    
    if not file_obj: 
        return
    
    file = file_obj.name
    
    window._mainLoop.create_task(
        runners.run_inkboard_config(file))
    
    return