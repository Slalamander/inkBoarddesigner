"""Library to interface with fbink in a more convenient manner.
See: https://github.com/NiLuJe/FBInk/blob/master/fbink.h#L621 for the full library
See: https://github.com/NiLuJe/py-fbink/blob/master/fbink_build.py for the available python bindings.

Usage: `from fbink import API as FBInk`
"""

from typing import * 
import functools, os, subprocess, time, logging

if TYPE_CHECKING:
    from .fbink_mock import ffi, lib as FBInk
    from PIL import Image
else:
    from _fbink import ffi, lib as FBInk

VERBOSE = int(logging.DEBUG/2)
_LOGGER = logging.getLogger(__name__)

ffi_typedef = TypeVar("typedef")
ffi_struct = TypeVar("struct")
ffi_union = TypeVar("union")

T = TypeVar('T')
class classproperty(Generic[T]):
    "Used to avoid the deprecation warning (and the extra writing) needed to set class properties"
    
    def __init__(self, method: Callable[..., T]):
        self.method = method
        functools.update_wrapper(self, wrapped=method) # type: ignore

    def __get__(self, obj, cls=None) -> T:
        if cls is None:
            cls = type(obj)
        return self.method(cls)

class API:
    """Wrapper around the FBInk lib class with doc strings and type hints were possible.

    An API to interface and print stuff on E-ink devices with NiLuJe's Kobo stuff installed, which comes with the FBInk library and python bindings.
    I am by no means an expert, so the implemented methods are only for stuff I understand/needed.
    Upon being garbage collected, the class itself should take care of closing the framebuffer.

    The API has class properties for certain values from the state struct, like the device name and the screen size e.g.
    You can call `API._unused_state_attributes` to get a list of all the unused attributes available in the FBInkState struct, and use `get_state_attribute` to get its value.
    """    

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls,"__instance"):
            cls.__instance = object.__new__(cls)
            return cls.__instance 
        else:
            return cls.__instance
    
    @classmethod
    def __init__(cls):
        cls._fbink_cfg = ffi.new("FBInkConfig *")
        cls._fbink_dumpcfg = ffi.new("FBInkDump *")

        cls._is_quiet = 1
        cls._fbink_cfg.is_quiet = cls._is_quiet
        cls._fbfd = FBInk.fbink_open()
        FBInk.fbink_init(cls._fbfd, cls._fbink_cfg)
        cls._state = ffi.new("FBInkState *")
        cls.get_state()
        v = cls.fbink_version()
        if "for" in v:
            v, plt = v.split(" for ")
        else:
            plt = None
        
        cls._version = v
        cls._platform = plt

    @classmethod
    def __del__(cls):
        FBInk.fbink_close(cls._fbfd)
        print("fbink closed")

    @classmethod
    def close(cls):
        FBInk.fbink_close(cls._fbfd)

    @classmethod
    def get_state(cls):
        cls.fbink_reinit()
        state = cls._state
        FBInk.fbink_get_state(cls._fbink_cfg, state)

        ##For the definition of all attributes of state, see:
        ##https://github.com/NiLuJe/FBInk/blob/master/fbink.h#L621
        for attr in state.__dir__():
            val = getattr(state,attr)
            if isinstance(val, ffi.CData):
                val = ffi.string(val)
                if isinstance(val,bytes):
                    val = val.decode("ascii")
            attr_name = f"_{attr}"
            setattr(cls,attr_name, val)
        cls._state = state
    
    @classmethod
    def get_state_attribute(cls, attribute: str) -> Any:
        "Returns the requested state attributes value."
        if hasattr(cls, f"_{attribute}"):
            return getattr(cls, f"_{attribute}")
        return getattr(cls._state, attribute)
    
    @classmethod
    def _unused_state_attributes(cls):
        """Prints out any properties of the state struct not available as class property
        May be useful when the python bindings are updated (seems to be happening as some c functions like `fbink_target` are unavailable.)
        Though it may simply be due to using an older device, the python bindings have not been updated as recently as the main library, but that may come when a new release of kobo stuff is uploaded.
        """
        
        missing = []
        for attr in cls.__state.__dir__():
            if not hasattr(cls,attr):
                missing.append(attr)
        
        if missing:
            print("FBInk API does not have the following state properties defined:")
            for attr in missing: print(attr)

    @classmethod
    def _all_waveforms(cls) -> list[str]:
        wfms = []
        for attr in FBInk.__dict__:
            if "WFM" in attr:
                wfms.append(attr)
        return wfms
    
    @classmethod
    def _all_methods(cls) -> list[Callable]:
        ms = []
        for attr, val in FBInk.__dict__.items():
            if callable(val):
                ms.append(attr)
        return ms

    @classmethod
    def _ffi_types(cls) -> tuple[list[ffi_typedef],list[ffi_struct],list[ffi_union]]:
        "Returns the available ffi types available"
        return ffi.list_types()

    #region
    @classproperty
    def version(cls) -> str:
        "The fbink version"
        return cls._version
    
    @classproperty
    def platform(cls) -> str:
        "The fbink platform, e.g. Kobo or Kindle. None if unknown"
        return cls._platform

    @classproperty
    def device_name(cls) -> str:
        "The name/model of the device"
        return cls._device_name

    @classproperty
    def device_codename(cls) -> str:
        "Codename of the device"
        return cls._device_codename
    
    @classproperty
    def device_platform(cls) -> str:
        "Platform of the device (board type, not brand name)"
        return cls._device_platform

    @classproperty
    def device_id(cls) -> int:
        "The id of the device, used by fbink to determine the model"
        return cls._device_id

    @classproperty
    def screen_width(cls) -> int:
        "Total width of the screen in pixels"
        return cls._screen_width

    @classproperty
    def screen_height(cls) -> int:
        "Total height of the screen in pixels"
        return cls._screen_height
    
    @classproperty
    def view_width(cls) -> int:
        "Viewable width of the screen in pixels (Taking bezels into account)"
        return cls._view_width
    
    @classproperty
    def view_height(cls) -> int:
        "Viewable height of the screen in pixels (Taking bezels into account)"
        return cls._view_height
    
    @classproperty
    def max_rows(cls) -> int:
        return cls._max_rows
    
    @classproperty
    def max_cols(cls) -> int:
        return cls._max_cols

    @classproperty
    def screen_dpi(cls) -> int:
        "DPI (resolution) of the screen"
        return cls._screen_dpi
    
    @classproperty
    def current_rota(cls) -> int:
        "Current rotation as reported by the device"
        return cls._current_rota

    @classproperty
    def current_rota_canonical(cls):
        "Current rotation converted to canonical rotation (0 for upright portrait)"
        return FBInk.fbink_rota_native_to_canonical(cls.current_rota)

    @classproperty
    def can_rotate(cls) -> bool:
        "True if the device can rotate (i.e. has a gyro)"
        return cls._can_rotate

    @classproperty
    def can_hw_invert(cls) -> bool:
        "True if the device supports hardware screen inversion"
        return cls._can_hw_invert
    #endregion

    #region
    @classmethod
    def fbink_version(cls) -> str:
        "Prints the fbink version"
        return ffi.string(FBInk.fbink_version()).decode("ascii")

    @classmethod
    def fbink_reinit(cls):
        FBInk.fbink_reinit(cls._fbfd, cls._fbink_cfg)

    @classmethod
    def fbink_print(cls, string: str):
        "Prints a string on the top of the screen"
        FBInk.fbink_print(cls._fbfd, string.encode("utf-8"), cls._fbink_cfg)

    @classmethod
    def fbink_refresh(cls, x: int, y: int, w: int, h: int):
        "Refreshes the screen in the provided region"
        FBInk.fbink_refresh(cls._fbfd, y,x,w,h, cls._fbink_cfg)

    @classmethod
    def fbink_print_image(cls, image_file: str, x_off: int, y_off: int):
        "Prints the image file onto the screen"
        FBInk.fbink_print_image(cls._fbfd, image_file, x_off, y_off, cls._fbink_cfg)

    @classmethod
    def fbink_print_raw_data(cls, data: str, w: int, h: int, length, x_off: int, y_off: int):
        "Prints the raw data as pixels onto the screen"
        FBInk.fbink_print_raw_data(cls._fbfd, data, w, h, length, x_off, y_off, cls._fbink_cfg)

    @classmethod
    def fbink_print_pil(cls, image: "Image.Image", x: int = 0, y: int = 0):
        """Convenience method to print a PIL image instance to the screen.
        
        Wrapper around `API.fbink_print_raw_data`, as the function decodes the provided image into raw data.

        Parameters
        ----------
        image : Image.Image
            The image object to print
        x : int, optional
            x coordinates of the topleft corner in pixels, by default 0
        y : int, optional
            y coordinates of the topleft corner in pixels, by default 0
        """        
        ""
        if image.mode == "P":
            _LOGGER.debug("Image is paletted, translating to actual values")
            image = image.convert()

        # If image is not grayscale, RGB or RGBA (f.g., might be a CMYK JPEG) convert that to RGBA.
        if image.mode not in ["L", "LA", "RGB", "RGBA"]:
            _LOGGER.debug("Image data is packed in an unsupported mode, converting to RGBA")
            image = image.convert("RGBA")

        # And finally, get that image data as raw packed pixels.
        raw_data = image.tobytes("raw")
        raw_len = len(raw_data)
        _LOGGER.log(VERBOSE,"Raw data buffer length: {}".format(raw_len))

        cls.fbink_print_raw_data(raw_data, image.width, image.height, raw_len, x, y)

    @classmethod
    def fbink_cls(cls, rect):
        "Clears the screen region of the given rectangle pointer"
        FBInk.fbink_cls(cls._fbfd, cls._fbink_cfg, rect)

    @classmethod
    def fbink_grid_clear(cls, cols: int, rows: int):
        "Clears the screen region up to the given column and row"
        FBInk.fbink_grid_clear(cls._fbfd, cols, rows, cls._fbink_cfg)

    @classmethod
    def fbink_grid_refresh(cls, cols, rows):
        "Refreshes the screen up to the given column and row"
        FBInk.fbink_grid_refresh(cls._fbfd, cols, rows, cls._fbink_cfg)
    
    @classmethod
    def fbink_invert_screen(cls):
        "Inverts the screen using software inversion"
        FBInk.fbink_invert_screen(cls._fbfd, cls._fbink_cfg)

    #endregion

    @classmethod
    def screen_clear(cls):
        "Clears the entire screen"
        cls.fbink_grid_clear(cls.max_cols, cls.max_rows)
    
    @classmethod
    def screen_refresh(cls):
        "Refreshes the entire screen"
        cls.fbink_grid_refresh(cls.max_cols, cls.max_rows)

    @classmethod
    def set_waveform(cls, mode: str = "AUTO"):
        if mode == "AUTO":
            mode = "WFM_AUTO"
        try:
            if mode == None:
                raise AttributeError
            mode = mode.upper().replace(" ", "_")
            val = getattr(FBInk,mode)
            cls._fbink_cfg.wfm_mode = val
        except AttributeError:
            print(f"Invalid wafeform value {mode}")
            cls._fbink_cfg.wfm_mode = FBInk.WFM_AUTO

    @classmethod
    def rotate_screen(cls, rota: int = None):
        """Rotates the screen. 
        
        If rota is not passed, will rotate 90 degrees clockwise.
        Passes the command 'fbdepth -R' to the os, since rotation via the Python bindings seemed impossible.
        """
        if rota == cls.current_rota_canonical:
            return
        
        if rota == None:
            rota = cls.current_rota_canonical + 1 if cls.current_rota_canonical < 3 else 0
        
        if rota > 3:
            _LOGGER.warning("Rotation cannot be larger than 3")
            return
        
        _LOGGER.debug(f"Rotating device from {cls.current_rota_canonical} to {rota}")

        cmd = ["fbdepth", "-R", str(rota)]
        if cls._is_quiet:
            cmd.append("-q")
        subprocess.call(cmd)
        cls.get_state()
        cls.screen_clear()
        cls.screen_refresh()

API()