
from PIL import Image, ImageDraw

from PythonScreenStackManager.elements import Element, GridLayout, Layout, Button
from PythonScreenStackManager.elements.baseelements import colorproperty, elementaction
from PythonScreenStackManager.pssm.styles import Style
from PythonScreenStackManager.pssm_types import ColorType
from PythonScreenStackManager.tools import DrawShapes

##stopwatch element (using text) for showing of tiles and some more advanced features
##Will write that later.

class DrawToggle(Element):
    """An example of how to make a custom element.

    A toggle element already exists, using the _BoolElement class.
    Since this element functions as an example, it will be made from the ground up (i.e. solely based on Element.)
    The `ToggleElement` can however be used as a reference to compare how various base classes can be implemented.
    """

    def __init__(self, handle_color: ColorType = "blue", on_color: ColorType = "yellow", off_color: ColorType = "red",  **kwargs):
        
        super().__init__( **kwargs) ##This passes all keyword arguments to the base Element init. 
                                    ##This has to always be called to set all required properties correctly.
        
        self.handle_color = handle_color
        self.on_color = on_color
        self.off_color = off_color

        self.__toggleState = True

    #Not required, but for properties I generally use the writing conventions as follows:
        ##snake_case: properties that can be set by the user
        ##camelCase: properties that cannot (directly) be set by the user, i.e. they require a function to be called.

    @property
    def toggleState(self) -> bool:
        "The current state of the toggle"
        return self.__toggleState

    @colorproperty.NOT_NONE
    def handle_color(self) -> ColorType:
        "Color of the toggle circle"
        ##The @colorproperty decorator automatically applies the logic for setting and getting colors.
        ##This means it will be able to retrieve color values from its parents as well.
        ##The Not_NONE parameter indicate the toggle must have a color, and cannot be transparent.
        return self._handle_color
    
    @colorproperty
    def on_color(self) -> ColorType:
        "Color of the slide part when the toggle is on"
        return self._on_color
    
    @colorproperty
    def off_color(self) -> ColorType:
        "Color of the slide part when the toggle is off"
        return self._off_color
    
    def generator(self, area = None, skipNonLayoutGen = False):
        ##The generator is the base function that draws elements.
        ##This generator will show how to create an element from scratch.

        if area != None:
            self._area = area

        [(x,y),(w,h)] = self.area

        ##First, setup the base image that the element will be drawn on. It is instantiated by getting the correct background color, and making a new PIL Image object with it.
        background_color = Style.get_color(self.background_color, self.screen.imgMode)
        base_img = Image.new(self.screen.imgMode, (w,h), background_color)

        ##convert_dimension can be used to convert pssm dimension strings into their integer values for their element.
        relative_height = "h*0.4"
        relative_width = "w*0.5"
        (slider_h, slider_w) = self._convert_dimension((relative_height, relative_width))

        x_c, y_c = (int(w/2), int(h/2))

        xy = [(x_c - int(slider_w/2), y_c - int(slider_h/2)), (x_c + int(slider_w/2), y_c + int(slider_h/2))]

        if self.toggleState:
            slide_color = self.on_color
        else:
            slide_color = self.off_color
        slide_color = Style.get_color(slide_color, base_img.mode)

        ##We could use the ImageDraw library directly to draw shapes, however it has some issues with the quality of returned images.
        ##The DrawShapes tool should generally take core of this. The type hinting is sadly not very present, but can be found in the PIL docs for each function.
        ##Don't need to do anything with the output, as it is the base image.
        DrawShapes.draw_rounded_rectangle(base_img, drawArgs={"fill": slide_color, "xy": xy})

        circle_r = int(slider_h*0.75)

        ##Depending on the state, the location of the handle circle differs.
        ##If on (True), it is on the right, otherwise on the left.
        ##The code below determines the correct position of the center x coordinate, and from there calculates the bounding box (needed for the draw_circle function.)
        if self.toggleState:
            circle_x = xy[1][0]
        else:
            circle_x = xy[0][0]

        circle_xy = [(circle_x - circle_r, y_c - circle_r), (circle_x + circle_r, y_c + circle_r)]
        circle_col = Style.get_color(self.handle_color)

        ##Finally, draw the circle onto our image, and we have something that looks like a toggle.
        DrawShapes.draw_circle(base_img, {"xy": circle_xy, "fill": circle_col})

        return base_img
    
    def toggle(self):
        """Non async method for toggling.
        
        The non async method does basically the same as the async method. The call to update is internally forwarded to async_update.
        """
        self.__toggleState = not self.__toggleState
        self.update(updated=True) 
        ##By passing updated=True, we indicate to the updater that an attribute has changed outside the updater.
        ##When not passed, the updater will check if attributes to set are different than their current value, and determine whether to regenerate accodingly.
        return

    async def async_toggle(self):
        "Toggles the element, but uses async. Generally preferred."
        self.__toggleState = not self.__toggleState
        await self.async_update(updated=True)

    @elementaction
    def tap_action(self):
        "The function to call when tapping (short clicking) the toggle"

        ##This way, we intercept any calls to tap_action to automatically change the element's state.
        ##This happens regardless of what the user sets as tap_action (i.e. setting it to None will still toggle it)
        self.toggle()
        return self._tap_action


class LabeledElements(GridLayout):

    def __init__(self, elements, **kwargs):
        
        labelelts = []
        for elt in elements:
            labelelts.append(self.create_element_label(elt))

        super().__init__(labelelts, **kwargs)

    def create_element_label(self, element: Element) -> Layout:
        elt_name = element.__class__.__name__
        label = Button(elt_name, fit_text=True, radius="h*0.15", background_color="white")

        id = f"{element.id}_layout"

        labellayout = [["?", (element,"w")], ["h*0.2", (label, "w")]]
        return Layout(labellayout, id=id,
                    grid_row=getattr(element,"grid_row", None), grid_column=getattr(element,"grid_column", None))

