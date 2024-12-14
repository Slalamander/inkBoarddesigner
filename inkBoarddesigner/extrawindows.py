
import tkinter as tk

##These are dependent on the device being emulated.
##So probably keep the set device function and set that when setting up the device

class backlight_window:
    def __init__(self):
        self.window = ttk.Toplevel(title="Backlight Settings")

        frame = ttk.Frame(self.window)
        frame.grid(column=0, row=0, sticky="nsew")

        ##Simulate toggle
        toggleFrame = ttk.Labelframe(frame,text="Simulate", style='toggleCenter.TLabelframe', labelanchor="n", cursor="hand2")
        toggleFrame.grid_columnconfigure(0, weight=1)
        ToolTip(toggleFrame, "Place a semi-transparent dark rectangle over the screen, to simulate the backlight. Rectangle becomes more transparent when brightness goes up.",  bootstyle=("dark","inverse"))
        var = tk.BooleanVar(device.window,name="backlight")
        toggleFrame.bind("<Button-1>",func=partial(bool_toggle,var))
        toggle = ttk.Checkbutton(toggleFrame, 
                        onvalue = 1, offvalue = 0, style='Roundtoggle.Toolbutton', 
                        variable=var)
        toggle.grid(column=0, row=0)
                        # variable=tkvar, command=command, cursor="hand2")
        toggleFrame.grid(row=0, column=1, sticky="nsew", pady=(10,0))

        ##Behaviour list
        val = device.parentPSSMScreen.backlightBehaviour
        self.backlightBehv = ttk.StringVar(master=device.window, name="backlight.behaviour")
        self.backlightBehv.trace_add("write",self.__set_behaviour)
                
        ops = ["Manual", "On Interact", "Always"]
        behvFrame = ttk.Labelframe(frame,text="Behaviour", style='toggle.TLabelframe', labelanchor="w")
        behv = ttk.Combobox(behvFrame, textvariable=self.backlightBehv, values=ops, state="readonly", width=25, cursor="hand2")
        behv.set(val)
        behv.grid(row=0,column=0)
        behvFrame.grid(row=0,column=0)
        ToolTip(behvFrame,"Backlight behaviour. Manual means it only turns on/off when called explicitly. On Interact means it turns on when interacting with the screen. Always means it is always on by default (can be turned on/off via functions). Initial behaviour is set in configuration.yaml", bootstyle=("dark","inverse"))

        #Brightness slider
        brtFrame = ttk.Labelframe(frame,text="Brightness", style='toggle.TLabelframe', labelanchor="w")
        brtFrame.columnconfigure(0,weight=1)
        # brt = device.backlight.brightness
        var : tk.IntVar = FEATURE_VARIABLES["backlight"]["brightness"]
        brtSlide = ttk.Scale(brtFrame, command=self.__set_brightness, name="brightness",  from_=0, to=100, length=None, cursor="hand2", variable=var)
        brtSlide.grid(row=0,column=0, sticky="ew")
        brtFrame.grid(row=1, column=0, sticky="ew", columnspan=2)
        brtSlide.bind('<Button-1>', set_slider_left_click)

        #defaultBrightness slider
        defbrtFrame = ttk.Labelframe(frame,text="Default Brightness", style='toggle.TLabelframe', labelanchor="w")
        defbrtFrame.columnconfigure(0,weight=1)
        var : tk.IntVar = FEATURE_VARIABLES["backlight"]["defaultBrightness"]
        defbrtSlide = ttk.Scale(defbrtFrame, command=self.__set_default_brightness, name="default_brightness",  from_=0, to=100, variable=var, length=None, cursor="hand2")
        defbrtSlide.grid(row=0,column=0, sticky="ew")
        defbrtFrame.grid(row=2, column=0, sticky="ew", columnspan=2)
        defbrtSlide.bind('<Button-1>', set_slider_left_click)
        ToolTip(defbrtFrame, "The default brightness (0-100) when turning on the backlight without specifying a brightness.", bootstyle=("dark","inverse"))

        ##Spinboxes
        spFrame = ttk.Frame(frame)
        spFrame.grid(row=3, columnspan=2)
        digit_func = device.window.register(validate_positive_number)

        ##Default transition time
        trFrame = ttk.Labelframe(spFrame,text="Transition Time", style='toggle.TLabelframe', labelanchor="n")
        trFrame.columnconfigure(0,weight=1)
        var = tk.DoubleVar(device.window, name="backlight.defaultTransition")
        self.trBox = ttk.Spinbox(trFrame, from_=0.0, to=60*60, command=self.__set_default_transition ,validate="key", validatecommand=(digit_func, '%P', "%W"))
        # var.set(device.backlight.defaultTransition)
        # self.trBox.set(device.backlight.defaultTransition)
        self.trBox.set(var.get())
        self.trBox.grid(row=0,column=0, sticky="ew")
        trFrame.grid(row=0, column=0)
        ToolTip(trFrame, "The default transition time (in seconds) when turning on/off the backlight without specifying a transition.", bootstyle=("dark","inverse"))

        ##Default on time
        offFrame = ttk.Labelframe(spFrame,text="Default on time", style='toggle.TLabelframe', labelanchor="n")
        offFrame.columnconfigure(0,weight=1)
        var = tk.DoubleVar(device.window, name="backlight.time_on")
        var.set(device.parentPSSMScreen.backlight_time_on)
        # var.trace_add("write", self._trace_setting)
        # digit_func = device.window.register(validate_default_transition)
        self.offBox = ttk.Spinbox(offFrame, from_=0.0, to=60*60, command=self.__set_turn_off_time ,validate="key", validatecommand=(digit_func, '%P', "%W"))
        # self.offBox.set(device.parentPSSMScreen.backlight_time_on)
        self.offBox.set(var.get())
        self.offBox.grid(row=0,column=0, sticky="ew")
        offFrame.grid(row=0, column=1)
        ToolTip(offFrame, "The default time the backlight stays on for (in seconds) when calling the screen's temporary backlight function without specifying a time.", bootstyle=("dark","inverse"))

        ##Minimum brightness setting?
        ##Maybe something for later though when setting up more devices

    def __set_behaviour(self, *args):
        n = self.backlightBehv.get()
        # device.parentPSSMScreen.backlightBehaviour = n
        device.parentPSSMScreen.set_backlight_behaviour(n)

    def __set_brightness(self, *args):
        # val = brtSlide.get()
        var : tk.IntVar = FEATURE_VARIABLES["backlight"]["brightness"]
        val = var.get()
        device.backlight.turn_on(int(val), transition=0)

    def __set_default_brightness(self,*args):
        var : tk.IntVar = FEATURE_VARIABLES["backlight"]["defaultBrightness"]
        val = var.get()
        device.backlight.defaultBrightness = int(val)

    def __set_default_transition(self,*args):
        # v = args
        # val = trBox.get()
        # var : ttk.DoubleVar = FEATURE_VARIABLES["backlight"]["defaultTransition"]
        # val = var.get()
        # arg = args
        # var = device.window.getvar("backlight.defaultTransition")
        var : ttk.DoubleVar = FEATURE_VARIABLES["backlight"]["defaultTransition"]
        val = self.trBox.get()
        device.backlight.defaultTransition = float(val)
        var.set(float(val))
        return
    
def show_backlight_window(event : tk.Event = None):
    "Shows the window with battery settings"
    backlight_window()