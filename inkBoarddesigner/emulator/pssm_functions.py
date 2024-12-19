"Functions that require pssm (i.e. a running inkBoard instance) to interface with the designer"

import logging
from typing import TYPE_CHECKING, Optional
import tkinter as tk
import tkthread


from PIL import ImageTk

import ttkbootstrap as ttk
from ttkbootstrap.tooltip import ToolTip

import inkBoard
from inkBoard import core as CORE

from PythonScreenStackManager import elements

from .. import const
from ..settings import EM_SETTINGS

from ..tkinter import window, functions as tk_functions
from ..tkinter.windows import TreeFrame, ElementWindow
from ..tkinter.widgets import Treeview

if TYPE_CHECKING:
    from PythonScreenStackManager.pssm.screen import PSSMScreen

_LOGGER = inkBoard.getLogger(__name__)


##Just call unbind first them
##Things to (re)bind: the listvariable/combobox
##Refresh Tree button
##Highlight Switch
##Backlight function
##Screenshot function

current_tree = None

MDI_TREE_ICONS = {}
ELEMENT_ICONS_TK = {}
ENTITY_ICONS_TK = {}

_ELEMENT_DICT = {}
_INDICATOR_RECTANGLES = []

ui_frame: ttk.Frame = window.children[const.UI_FRAME_NAME]
tree_frame: TreeFrame = ui_frame.children[const.TREE_FRAME_NAME]
canvas: tk.Canvas = window.children[const.CANVAS_NAME]

tree_frame.last_hover = False

##These do not get imported in the window thread.
def build_tk_icon(icon: str) -> ImageTk.PhotoImage:
    "Builds icon for the treeview in the correct thread"
    
    return tk_functions.build_tree_icon(icon)

ELEMENT_ICONS_TK["default"] = build_tk_icon(const.DEFAULT_ELEMENT_ICON)
ENTITY_ICONS_TK["default"] = build_tk_icon("mdi:one-up")

def add_element_icon(element : "elements.Element"):
    
    icon = element._emulator_icon
    icon = build_tk_icon(icon)
    ELEMENT_ICONS_TK[str(element.__class__.__name__)] = icon

@tkthread.called_on_main
def build_element_tree(screen: "PSSMScreen", open_items: bool = False):

    eltStack = screen.stack

    treeview = tree_frame.get_tree("Elements")

    open_init = open_items

    def make_layout_tree(layoutElt : "elements.Layout", parentiid : str):
        
        if isinstance(layoutElt, elements.TabPages):
            eltList = set(layoutElt.create_element_list()) | set(layoutElt.pageElements)
        else:
            eltList = layoutElt.create_element_list()


        for elt in eltList:
            elt : elements.Layout
            if not getattr(elt, "_isSubLayout", False) or (elt.__class__ not in  {elements.Layout, elements.baseelements._TileBase}):
                if elt.id == elt.unique_id:
                    eltname = elt.id.replace('_',' ')
                else:
                    eltname = elt.id
                elttype = str(elt.__class__.__name__)
                if elttype not in ELEMENT_ICONS_TK:
                    add_element_icon(elt)
                    _LOGGER.verbose(f"Made new icon for {elt}")
                icon = ELEMENT_ICONS_TK.get(elttype, ELEMENT_ICONS_TK["default"])
                iid = elt.id
                entity = getattr(elt,"entity","None")
                if not treeview.exists(iid):
                    treeview.insert(
                            parentiid,
                            tk.END,
                            iid = iid,
                            text=eltname,
                            values=(entity),
                            image=icon,
                            open=open_init
                        )
                    _ELEMENT_DICT[iid] = elt
                else:
                    if iid in treeview.get_children(parentiid):
                        pass
                    else:
                        treeview.reattach(iid, parentiid, tk.END)
            else:
                iid = parentiid

            if isinstance(elt,elements.Layout):
                make_layout_tree(elt, iid)

    for elt in eltStack:
        eltname = elt.id.replace('_',' ')
        elttype = str(elt.__class__.__name__)
        if elttype not in ELEMENT_ICONS_TK:
                add_element_icon(elt)
        icon = ELEMENT_ICONS_TK.get(elttype, ELEMENT_ICONS_TK["default"])
        iid = elt.id
        entity = getattr(elt,"entity","None")

        if not treeview.exists(iid):
            treeview.insert(
                "",
                tk.END,
                iid = iid,
                text=eltname,
                values=(entity),
                image=icon,
                open=open_init
            )
            _ELEMENT_DICT[iid] = elt

        if isinstance(elt,elements.Layout):
            make_layout_tree(elt, iid)

        for id, elt in screen.popupRegister.items():
            eltname = id
            elttype = str(elt.__class__.__name__)
            if elttype not in ELEMENT_ICONS_TK:
                    add_element_icon(elt)
            icon = ELEMENT_ICONS_TK.get(elttype, ELEMENT_ICONS_TK["default"])
            iid = elt.id
            entity = getattr(elt,"entity","None")

            if iid in treeview.get_children():
                treeview.delete(iid)

            treeview.insert(
                "",
                tk.END,
                iid = iid,
                text = eltname,
                values=(entity),
                image = icon,
                open = open_init
            )
            _ELEMENT_DICT[iid] = elt
            if isinstance(elt,elements.Layout):
                make_layout_tree(elt, iid)

    treeview.enable()
    return

def element_tree_selected(tree: Treeview, event, iid):
    "Figure out which element was selected in the element tree, and pass it on to the indicator function"
    if not EM_SETTINGS.getboolean(const.HIGHLIGHT_VAR_NAME):
        return
    
    eltList = []
    for iid in tree.selection():
        eltList.append(_ELEMENT_DICT[iid])
    
    highlight_element(*eltList)

def get_element(element_id) -> Optional[elements.Element]:
    return CORE.screen.elementRegister.get(element_id,None)

def tree_hover(tree, event, iid):
    if iid in CORE.screen.elementRegister:
        show_element_tip(tree, iid)

def tree_click(event: tk.Event):
    "Handles tree clicks not in an element"

    tree = event.widget
    if not tree.identify_row(event.y):
        for item in tree.selection():
            tree.selection_remove(item)
        highlight_element()

def tree_double_click(tree, event: tk.Event, iid):

    elt = get_element(iid)
    if elt:
        ElementWindow(elt)
    return


def tree_leave(event):
    tree = tree_frame.tree
    tree_frame.tree_tip.hide_tip()
    if not tree: return

    if tree_frame.last_hover:
        tree_frame.tree_tip.hide_tip()
        tree.item(tree_frame.last_hover, tags=[])
        tree_frame.last_hover = None

    return

def highlight_element(*element_list : "elements.Element"):
    "Pass items to draw a square around. Removes currently drawn squares first."
    _LOGGER.verbose(f"Removing {len(_INDICATOR_RECTANGLES)} rectangles.")
    for rect in canvas.find_above(const.SCREEN_TAG):
        ##If this throws errors after clearing: either use find_above and just delete them from there
        ##Just need to know the tag of the screen image itself.
        canvas.delete(rect)

    _INDICATOR_RECTANGLES.clear()

    if not EM_SETTINGS.getboolean(const.HIGHLIGHT_VAR_NAME):
        return

    for elt in element_list:
        _LOGGER.debug(f"Selected element in area {elt.area}")
        if elt.area == None or not elt.onScreen:
            continue
        [(x,y),(w,h)] = elt.area
        rect = canvas.create_rectangle(x,y,x+w,y+h, outline="red",
                                    dash=(5,2),width=5)
        _INDICATOR_RECTANGLES.append(rect)

def show_element_tip(tree: Treeview, event, element_id):
    
    if element_id not in CORE.screen.elementRegister:
        return

    elt = CORE.screen.elementRegister[element_id]

    tipText = (f"""{elt.__class__.__name__}: {element_id}\n
            Double click to view more info""")
    
    tree.tooltip.text = tipText
    
    tree.tooltip.show_tip()
    return

def highlight_setting(var_name, var_index, mode):

    highlight_element()

    val = window.hightlight_variable.get()

    tree_frame.update()

def __tree_list_setting(var_name, var_index, mode):
    if mode == 'write':
        window.trace_variable(var_name,var_index,mode)

    var_val = window.tree_list_variable.get()
    _LOGGER.debug(f"List has changed. Value is {var_val}")
    
    highlight_element() #Removes any highlights when the list changes

    if var_val == "Elements":
        tree_frame.entity_tree.pack_forget()
        tree_frame.element_tree.pack(anchor=tk.S, fill=tk.BOTH, expand=1)
        _LOGGER.debug("dont forget to rebuild the tree!")
    elif var_val == "Entities":
        tree_frame.element_tree.pack_forget()
        tree_frame.entity_tree.pack(anchor=tk.S, fill=tk.BOTH, expand=1)
        _LOGGER.debug("dont forget to rebuild the tree!")
    else:
        tree_frame.element_tree.pack_forget()
        tree_frame.entity_tree.pack_forget()
        if tree_frame.tree:
            tree_frame.tree_tip.hide_tip()
            tree_frame.unbind("<Enter>")
            tree_frame.unbind("<Leave>")
        return

    tree_frame.last_hover = False  

    tree_frame.tree_tip = ToolTip(tree_frame, bootstyle=const.TOOLTIP_STYLE)
    tree_frame.tree_tip.move_tip()
    tree_frame.tree_tip.hide_tip()



def import_funcs():

    element_tree = tree_frame.element_tree
    element_tree.on_select = element_tree_selected
    element_tree.on_double_click = tree_double_click
    element_tree.on_hover = show_element_tip

window.call_in_main_thread(import_funcs)