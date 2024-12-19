"Reference module for interfacing with fbink. Cannot guarantee functionality is completely as advertised on device."

from PIL import Image
from typing import *

class ffi():
    def __init__(self):
        self.is_centered = False
        self.is_halfway = False

    @staticmethod
    def new(arg1):
        return lib

    @staticmethod
    def string(ctype: bytes) -> str:
        pass

    @staticmethod
    def list_types() -> tuple[
                    list[Literal["typedef_names"]],
                    list[Literal["names_of_structs"]],
                    list[Literal["names_of_unions"]]]:
        return

class lib():
    ##Gathered functions by calling help(lib) -> list is not exhaustive
    def __init__(self):
        pass

    @staticmethod
    def new(arg1):
        return ffi

    @staticmethod
    def fbink_init(arg1: int, fbinkconfig):
        """
        Initialize internal variables keeping track of the framebuffer's configuration and state, as well as the device's hardware.
        MUST be called at least *once* before any fbink_print*, fbink_dump/restore, fbink_cls or fbink_grid* functions.
        CAN safely be called multiple times,
            but doing so is only necessary if the framebuffer's state has changed (although fbink_reinit is preferred in this case),
            or if you modified one of the FBInkConfig fields that affects its results (listed below).
        Returns -(ENOSYS) if the device is unsupported (NOTE: Only on reMarkable!)
        fbfd:		Open file descriptor to the framebuffer character device,
        			if set to FBFD_AUTO, the fb is opened for the duration of this call.
        fbink_cfg:		Pointer to an FBInkConfig struct.
        			If you wish to customize them, the fields:
        			is_centered, fontmult, fontname, fg_color, bg_color,
        			no_viewport, is_verbose, is_quiet & to_syslog
        			MUST be set beforehand.
        			This means you MUST call fbink_init() again when you update them, too!
        			(This also means the effects from those fields "stick" across the lifetime of your application,
        			or until a subsequent fbink_init() (or effective fbink_reinit()) call gets fed different values).
        			NOTE: For fg_color & bg_color, see fbink_update_pen_colors().
        			NOTE: For is_verbose, is_quiet & to_syslog, see fbink_update_verbosity().
        NOTE: By virtue of, well, setting global variables, do NOT consider this thread-safe.
                The rest of the API should be, though, so make sure you init in your main thread *before* threading begins...
        NOTE: If you just need to make sure the framebuffer state is still up to date before an fbink_* call,
              (e.g., because you're running on a Kobo, which may switch from 16bpp to 32bpp, or simply change orientation),
               prefer using fbink_reinit instead of calling fbink_init *again*, as it's tailored for this use case.
               c.f., KFMon for an example of this use case in the wild.
        NOTE: You can perfectly well keep a few different FBInkConfig structs around, instead of modifying the same one over and over.
               Just remember that some fields *require* an fbink_init() call to be taken into account (see above),
               but if the only fields that differ don't fall into that category, you do *NOT* need an fbink_init() per FBInkConfig...
        """
        pass

    @staticmethod
    def fbink_version() -> bytes:
        pass

    @staticmethod
    def fbink_open():
        return True

    @staticmethod
    def fbink_close(arg1):
        pass

    @staticmethod
    def fbink_get_state(fbinkconfig, fbinkstate):
        pass

    @staticmethod
    def fbink_cls(arg1: int, fbinkconfig, fbinkrect, arg4: bool):
        pass

    @staticmethod
    def fbink_dump(arg1: int, fbinkdump):
        return
    
    @staticmethod
    def fbink_state_dump(fbinkconfig):
        "Dumps the fbink state in the console"
        return

    @staticmethod
    def fbink_free_dump_data(fbinkdump):
        return
    
    @staticmethod
    def fbink_get_fbinfo(fb_var_screeninfo, fb_fix_screeninfo):
        return
    
    @staticmethod
    def fbink_print_image(arg1, image_path, arg3, arg4, arg5):
        img = Image.open(image_path)
        img.show()

    @staticmethod
    def fbink_print_raw_data(arg1: int, raw_data, x: int, y: int, size_t, short1, short2, fbinkconfig):
        return
    
    @staticmethod
    def fbink_refresh(arg1: int, arg2: int, arg3: int, arg4: int, arg5: int, fbinkconfig):
        return
    
    @property
    def DATA(self):
        ##Doesn't work like this, each entry under DATA is it's own attribute
        return


    

