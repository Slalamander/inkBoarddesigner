"Runners for various important functions of the designer."

import tkthread
tkthread.patch()

from typing import TYPE_CHECKING
import inkBoard.packaging

import asyncio
import concurrent.futures
import threading

import sys
from pathlib import Path

import ttkbootstrap as ttk

import inkBoard
from inkBoard import constants as ib_const, core as CORE
from inkBoard.helpers import QuitInkboard, ConfigError, DashboardError, DeviceError, ScreenError

from . import util, const, _LOGGER
from .settings import save_settings

from .tkinter import window, functions as tk_functions
from .tkinter.builders import build_window
from .tkinter.functions import stop_emulator

if TYPE_CHECKING:
    import inkBoard.bootstrap
    import inkBoard.constants
    import inkBoard.helpers

importer_thread = concurrent.futures.ThreadPoolExecutor(None,const.IMPORTER_THREADPOOL)


def stop_designer():
    window._mainLoop.create_task(async_stop_designer())

async def async_stop_designer():
    save_settings()
    if hasattr(CORE,"screen"):
        try:
            stop_emulator(exce=SystemExit("Closing Designer"))
        except:
            pass
    
    if window._inkBoard_thread:
        window._inkBoard_thread.join(timeout=5)
    await asyncio.sleep(0)
    for task in asyncio.all_tasks():
        task.cancel()
    window.stop_update_loop()
    await asyncio.sleep(0)
    return

async def async_unload_inkBoard(reload_modules: bool = False):
    "Cancels all tasks running in the PSSM loop and reloads necessary modules."
    
    _LOGGER.debug(f"Unloading inkBoard")
    stop_loop = False
    if hasattr(CORE,"screen") and CORE.screen.mainLoop:
        CORE.screen.mainLoop.stop()
        stop_loop = CORE.screen.mainLoop
    
    await asyncio.to_thread(window._inkBoard_lock.acquire)
    await asyncio.to_thread(window._inkBoard_thread.join)

    if not hasattr(inkBoard, "core"):
        window._inkBoard_clean = True
        window._inkBoard_lock.release()
        return

    await asyncio.sleep(0)

    if hasattr(CORE,"screen"):
        for task in asyncio.all_tasks(CORE.screen.mainLoop):
            task.cancel()
    
    await asyncio.sleep(0)

    if reload_modules:
        ##Reloading the platform may actually be done already via the platform check
        await asyncio.to_thread(
            inkBoard.bootstrap.reload_core, CORE, True
                )
    else:
        await asyncio.to_thread(
            inkBoard.bootstrap.reload_core, CORE, False
                )
        ##Regarding that: move shorthand colors to style, so they can be reset from there.

    if stop_loop:
        stop_loop.close()

    window._inkBoard_clean = True
    window._inkBoard_lock.release()
    return

def unload_inkBoard(reload_modules: bool = False):
    t = window._mainLoop.create_task(async_unload_inkBoard(reload_modules))
    return t

async def reload_config(config, full_reload: bool = False):
    await unload_inkBoard(True)
    window.set_progress_bar(value=-1)
    window._mainLoop.create_task(run_inkboard_config(config))

async def run_inkboard_thread(config_file):
    
    reload_finally = True
    try:
        config_path = Path(config_file)
        config_folder = config_path.parent.absolute()
        custom_folder = config_folder / "custom"

        if window._inkBoard_lock.locked():
            _LOGGER.warning("Attempting to run new inkBoard thread before the last one has fully shut down.")

        window.set_progress_bar(1, text="Acquiring resources", title=f"Loading {config_path.name}")
        tkthread.call_nosync(window.configLabel.configure, 
                            text = config_path.name, cursor=const.INTERACT_CURSOR)

        window._inkBoard_lock.acquire()
        window._inkBoard_clean = False

        window.set_progress_bar(5, "Importing base functions")

        from inkBoard import core as CORE

        from .emulator import pssm_functions
        pssm_functions.CORE = CORE
        tk_functions.CORE = CORE

        _LOGGER.debug(f"CORE imported at {CORE.IMPORT_TIME}")

        from inkBoard import bootstrap 

        from .integrationloader import IntegrationLoader
        
        CORE.integration_loader = IntegrationLoader

        window.set_progress_bar(value=10, text="Gathering available integrations")
        folders = {"custom.integrations": custom_folder / "integrations"} | const.INTEGRATION_DIRS

        IntegrationLoader.get_integrations(folders)

        window.set_progress_bar(value=20, text="Importing PythonScreenStackManager")

        from PythonScreenStackManager.exceptions import ReloadWarning, FullReloadWarning

        window.set_progress_bar(value=25, text="Reading out base config")

        CORE.config = bootstrap.setup_base_config(config_file)

        bootstrap.setup_logging(CORE)

        window.set_progress_bar(30, "Importing integrations")
        CORE.integration_loader.import_integrations(CORE,window.set_progress_bar,(30,42))

        ##Is there a reason to not do this after setting up the screen and stuff?
        ##Except disallowing defining the screen outside of core
        CORE.custom_functions = bootstrap.import_custom_functions(CORE)

        bootstrap.import_custom_elements(CORE)

        ##Implement error catchers for these as well
        window.set_progress_bar(42, "Setting up emulator device")
        CORE.device = await bootstrap.setup_device(CORE)

        window.set_progress_bar(45, "Setting up PythonScreenStackManager screen")
        CORE.screen = await bootstrap.setup_screen(CORE)
        screen = CORE.screen
        screen.add_shorthand_function_group("custom", CORE.parse_custom_function)

        window.set_progress_bar(50, "Setting up styles")
        bootstrap.setup_styles(CORE)

        window.set_progress_bar(52, "Setting up integrations")
        max_integration_progress = 70
        CORE.integration_objects = await IntegrationLoader.async_setup_integrations(CORE, window.set_progress_bar, 
                                                                                (window._progressBar["value"],max_integration_progress))

        window.set_progress_bar(max_integration_progress, "Setting up dashboard")
        main_layout = bootstrap.setup_dashboard_config(CORE)

        window.set_progress_bar(75, "Readying screen")
        screen.clear()
        screen.start_batch_writing()

        window.set_progress_bar(77, "Starting integrations")
        await IntegrationLoader.async_start_integrations(CORE)

        window.set_progress_bar(90, "Preparing screen and elements for printing")
        await screen.async_add_element(main_layout, skipPrint=True)
        screen.stop_batch_writing()

        window.set_progress_bar(95, "Starting printing")

        try:
            done, pending = await asyncio.wait([bootstrap.run_core(CORE)], timeout=0.5)
            if pending:
                window.set_inkboard_state(ttk.ACTIVE)
                window.set_progress_bar(100, "Up and running")
                await asyncio.gather(*pending)
            else:
                for t in done:
                    _LOGGER.error(t.result())
                await asyncio.sleep(0)
                raise RuntimeWarning            
        except asyncio.CancelledError:
            window.set_inkboard_state(ttk.DISABLED)
        except ReloadWarning as exce:
            window.set_inkboard_state(ttk.DISABLED)
            if exce == FullReloadWarning or isinstance(exce, FullReloadWarning):
                full_reload = True
            else:
                full_reload = False
            window._mainLoop.create_task(reload_config(config_file, full_reload))
            reload_finally = False
        except QuitInkboard:
            window.set_inkboard_state(None)
            await asyncio.sleep(0)
        except SystemExit:
            window._inkBoard_lock.release() #Keeping this here to catch out the errors in IDE
            reload_finally = False
        except KeyboardInterrupt:
            stop_designer()
            
        except RuntimeError:
            pass
    except DashboardError as exce:
        CORE.screen.mainLoop.stop()
        _LOGGER.error(f"Error in dashboard config of file {config_file}: {exce}")
        window.set_inkboard_state("ERROR")
        window.set_progress_bar(ttk.DANGER, f"Error setting up dashboard: {exce}")
        await asyncio.sleep(0)
    except ConfigError as exce:
        _LOGGER.error(f"Error in config file {config_file}: {exce}")
        window.set_inkboard_state("ERROR")
        window.set_progress_bar(value=ttk.DANGER, text=f"Error in config file {config_file}: {exce}")
    except DeviceError as exce:
        msg = f"Error setting up inkBoard device: {exce}"
        _LOGGER.error(msg, exc_info=None)
        _LOGGER.debug(f"{type(exce)} info:", exc_info=exce)
        window.set_inkboard_state("ERROR")
        window.set_progress_bar(value=ttk.DANGER, text=msg)
    except ScreenError as exce:
        msg = "Error setting up pssm screen"
        _LOGGER.error(f"{msg}: {exce}")
        _LOGGER.debug(msg = f"{type(exce)} info:", exc_info=exce)
        window.set_inkboard_state("ERROR")
        window.set_progress_bar(value=ttk.DANGER, text=msg)
    finally:
        if window._inkBoard_lock.locked():
            window._inkBoard_lock.release()
        if reload_finally: 
            unload_inkBoard(True)
    return

async def run_inkboard_config(configuration, **kwargs):
    if window._inkBoard_thread:
        stop_emulator(exce=QuitInkboard("Loading new config"),new_state=ttk.DISABLED)
        await asyncio.sleep(0)
        await asyncio.to_thread(window._inkBoard_thread.join)
        await asyncio.sleep(0)
        await asyncio.to_thread(window._inkBoard_lock.acquire)
        await asyncio.sleep(0)
        await asyncio.to_thread(window._inkBoard_lock.release)
        if not window._inkBoard_clean:
            await unload_inkBoard()

    await asyncio.to_thread(window._inkBoard_lock.acquire)
    window._current_config_file = configuration
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_until_complete, kwargs={"future": run_inkboard_thread(configuration)}, name="inkBoard-thread")
    window._inkBoard_thread = thread
    thread.start()
    window._inkBoard_lock.release()
    return

async def async_run_designer(args):
    
    ##Settings for logging: same as run
    ##Config command: not required. For now, do not load anything if so, but will provide an option to open on the last opened config by default

    threading.excepthook = util.threading_except_hook
    tk_functions.runners = sys.modules[__name__]

    window = build_window()
    window.protocol("WM_DELETE_WINDOW", stop_designer)
    window.set_inkboard_state(None)

    if args.configuration:
        asyncio.create_task(run_inkboard_config(**vars(args)))
    await window.run_update_loop()
    return