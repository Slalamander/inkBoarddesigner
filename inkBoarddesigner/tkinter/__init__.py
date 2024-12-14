##Make the main window in here

from . import windows, widgets, functions

window = windows.DesignerWindow()
"The main window instance"

windows.window = window

functions.window = window
functions.windows = windows
functions.widgets = widgets

widgets.window = window