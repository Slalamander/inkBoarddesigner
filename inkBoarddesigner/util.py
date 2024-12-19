"Some utilities to use with the designer"

import logging
from typing import *
import asyncio
import inspect
from threading import ExceptHookArgs

from PIL import ImageTk

if TYPE_CHECKING:
    from .tkinter.windows import DesignerWindow

_LOGGER = logging.getLogger(__package__)

main_loop: asyncio.BaseEventLoop = None
window: "DesignerWindow"

iidType = TypeVar("iid", bound=str)

def threading_except_hook(*excepthooksargs):
    if not excepthooksargs: return
    args: ExceptHookArgs = excepthooksargs[0]
    if args.thread == window._inkBoard_thread:
        if window._inkBoard_lock.locked():
            window._inkBoard_lock.release()
    if args.exc_type not in {SystemExit, asyncio.CancelledError, RuntimeError}:
        if args.exc_value: raise args.exc_value
        else: raise args.exc_type()
    return


def call_in_main_thread(func : Callable, args, kwargs):
    
    if asyncio._get_running_loop() != main_loop != None:
        fut = asyncio.run_coroutine_threadsafe( #@IgnoreExceptions
            __call_in_main_thread(func,*args,**kwargs),
            main_loop)
        return fut.result()
    else:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            _LOGGER.error(f"Calling {func} with args {args} and kwargs {kwargs} caused an exception: {e}")
            raise e
    
async def __call_in_main_thread(func, *args, **kwargs):
    return func(*args, **kwargs)

class DummyTask:
    """
    Provides a dummy to mimic an asyncio task object when needed to make one before starting the event loop. For use in logic statements
    """
    
    def done(self) -> bool:
        """Returns True to mimic the task being done"""
        return True
    
    def cancelled(self) -> bool:
        """Returns False since the dummy task cannot be cancelled"""
        return False
    
    def cancel(self) -> None:
        """Does nothing but may be useful for logic purposes"""
        return
    
    def result(self) -> None:
        """Returns nothing since there is no result"""
        return

class ThreadSafeWidgetMeta(type):
    """Metaclass to use with subclassed tkwidgets. Wraps all object methods (not class or staticmethods!) into a threadsafe call for inkBoard designer.
    
    Generally not needed, since the designer used a thread-safe third party library for tkinter. However, for photoimages especially, this implementation functioned a lot faster.
    Be mindful using this as blocking call will block the event loop.
    """    

    def __new__(cls, name, bases, attrs):
        obj = super().__new__(cls, name, bases, attrs)
        for attr_name, attr_value in inspect.getmembers(obj, predicate=callable):
            if (attr_name.startswith("__") and attr_name.endswith("__") or
                attr_name == "cget"): ##Idk but cget causes issues with the TreeFrame at least and does not seem to interfere with the loop?
                continue

            if isinstance(attr_value,(classmethod,staticmethod)):
                continue

            setattr(obj,attr_name, cls.intercept_method_call(attr_value))
        return obj
    
    @staticmethod
    def intercept_method_call(method):
        def wrapper(*args, **kwargs):
            result = call_in_main_thread(method, args, kwargs)
            _LOGGER.verbose(f"Intercepted call to {method}")
            return result
        _LOGGER.verbose(f"Wrapped method {method}")
        return wrapper
    
class ThreadSafePhotoImage(ImageTk.PhotoImage, metaclass=ThreadSafeWidgetMeta):
    """Threadsafe implementation for calling photoimage, by passing the __init__ onto the main thread.
    
    Importing this module automagically changes the ImageTk.PhotoImage class to this one, to have it work correctly this module needs to be imported before imageTk is imported anywhere.
    Whilst tkthread also takes care of this, it appears to be a lot slower.
    """

    def __init__(self, image = None, size = None, **kw):
        call_in_main_thread(super().__init__,
                            (image, size), kw)
