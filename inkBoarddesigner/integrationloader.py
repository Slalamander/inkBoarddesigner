"""
Handler to load inkBoard integrations present in the designer etc. folder.
"""

import importlib.util
from typing import Callable, TYPE_CHECKING, Literal, Any
from types import MappingProxyType
import logging
from pathlib import Path
import sys
import asyncio
import json

from inkBoard import loaders
from inkBoard.helpers import classproperty, reload_full_module

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from inkBoard import core as CORE

class IntegrationLoader(loaders.IntegrationLoader):
    "Provides bindings to load inkBoard integrations including those in the designer."

    @classproperty
    def integration_keys(cls) -> dict[str,str]:
        return cls._integration_keys.copy()

    @classmethod
    def get_integrations(cls, folders: dict[str,Path]):
        #folders: dict with base module name mapped to the folder path
        cls._reset()

        for base_module, folder in folders.items():
            if folder.exists():
                cls._read_out_folder(base_module, folder)

        return MappingProxyType(cls._installed_integrations)
    
    @classmethod
    def add_integration_config_key(cls, key: str, module_name: str):
        if key in cls._integration_keys:
            int_mod = cls._integration_keys[key]
            _LOGGER.info(f"{key} is already used for a the config of a different integration: {int_mod}")
        else:
            cls._integration_keys[key] = module_name    ##This should go the other way around.
        return

    @classmethod
    def _read_out_folder(cls, base_module: str, folder: Path):
        folders = folder.iterdir()
        for int_dir in filter(lambda p: (p.is_dir() and not p.name.startswith("_")), folders):
            if int_dir.name in cls._installed_integrations:
                _LOGGER.info(f"Integration {int_dir.name} has already been found in module {cls._integration_modules[int_dir.name]}. Will not import from {base_module}")
                continue

            manifest = int_dir / "manifest.json"
            if not manifest.exists():
                _LOGGER.error(f"Integration folder {int_dir} is missing the manifest.json file.")
                continue

            with open(manifest) as f:
                manifest = json.load(f)
                ##Support for requirements has not yet been implemented
            
            if c := manifest.get("config_entry",False):
                #Will require config_keys, similar to esphome, which can be left empty if needed.
                name = f"{base_module}.{int_dir.name}"
                                        

                ##These should not be checked by config key (i.e., save the key in the dict entry); key should be the folder name.
                cls.add_integration_config_key(c, name)
                cls._installed_integrations[int_dir.name] = int_dir
                cls._integration_modules[int_dir.name] = name
            else:
                _LOGGER.error(f"Integrations are required to have a config_entry key {int_dir.name} does not")
                continue

    @classmethod
    def import_integrations(cls, core: "CORE", progress_func=None, value_range=()):
        config = core.config
        import_set: set[tuple[str, Path]] = set()

        ##Import custom via appending to path.
        ##And I think just import via here, but make the set or something recognise the base package too.
        ##Or save strings to the modules instead of their folders.

        for config_entry in cls._integration_keys:
            if config_entry in config.configuration:
                import_set.add((config_entry, cls._integration_keys[config_entry]))
        
        if not import_set: 
            return

        if progress_func:
            progress_func(value_range[0] + 1, f"Importing {len(import_set)} integrations")
            step = int((value_range[1] - value_range[0] - 1)/len(import_set))
            progress = value_range[0] + 1

        for (config_key, name) in import_set:
            integration = name.split(".")[-1]
            if progress_func:
                progress = progress + step
                progress_func(progress, f"Importing integration {integration}")
            module = cls._import_integration(name)
            if not module:
                _LOGGER.warning(f"Unable to successfully import integration {integration} from {name}")
            else:
                cls._imported_modules[integration] = module

        cls._reload_imports = False
        return
        ##See code in hass core: https://github.com/home-assistant/core/blob/ab5ddb8edfb72d5f5915574f642eba93afc5abdc/homeassistant/loader.py#L1669

    @classmethod
    def _import_integration(cls, name):
            
        module = None
        integration = name.split(".")[-1]

        ##Simply put: I don't think it'll matter how you set this up, the __init__ will be imported regardless
        ##Messing with the package name and whatever will just cause issues with relative imports and stuff
        ##So: make different file, like integration.py or something, that provided the hooks for the integration_loader
        ##Or simply make writers use the init to provide the correct hooks *shrug*

        spec = importlib.util.find_spec(f"{name}.designer")
        if spec:
            if f"{name}.designer" in sys.modules and cls._reload_imports:
                try:
                        reload_full_module(name)
                        module = sys.modules.get(name,None)
                except ImportError as exce:
                    _LOGGER.error(f"Unable to reload integration {name}, will try to import it again", exc_info=exce)
                    sys.modules.pop(name)
                _LOGGER.debug(f"Integration {name} has designer module")
            elif f"{name}.designer" in sys.modules:
                return sys.modules.get(f"{name}.designer",None)
            
            try:
                return cls._import_designer_module(integration, spec)
            except ImportError:
                return
        else:
            return super()._import_integration(name)

    @classmethod
    def _import_designer_module(cls, integration, spec):
        #Imports and verifies an integration's designer module. 
        #Overwrites the base setup function if present in the designer module
        
        designer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(designer_module) ##This step takes quite some time.
        base_module = designer_module.__name__.removesuffix(".designer")
        base_module = sys.modules.get(base_module)
        
        if hasattr(designer_module,"async_setup"):
            base_module.async_setup = designer_module.async_setup
        elif hasattr(designer_module, "setup"):
            ##Whilst it would be possible to make the designer setup etc. have priority even over base async_setup,
            ##I think it's better not to do so, since the designer module should try to exhibit roughly similar behaviour to the native integration
            base_module.setup = designer_module.setup
        
        if not hasattr(base_module,"async_setup") and not hasattr(base_module,"setup"):
            _LOGGER.warning(f"Integration {integration} is missing the required setup function")
            return
        
        if hasattr(designer_module,"async_start"):
            base_module.async_start = designer_module.async_start
        elif hasattr(designer_module,"start"):
            base_module.start = designer_module.start

        if hasattr(designer_module, "async_run"):
            base_module.async_run = designer_module.async_run

        return base_module

    @classmethod
    async def async_setup_integrations(cls, core: "CORE", progress_func=None, value_range=()) -> MappingProxyType[Literal["integration_entry"],Any]:
        integration_objects = {}
        
        config = core.config
        screen = core.screen

        if not cls._imported_modules:
            return MappingProxyType({})

        if progress_func:
            progress_func(value_range[0] + 1, f"Importing {len(cls._imported_modules)} integrations")
            step = int((value_range[1] - value_range[0] - 1)/len(cls._imported_modules))
            progress = value_range[0] + 1

        for integration, module in cls._imported_modules.items():
            module : "sys.ModuleType"
            setup_func = None
            if hasattr(module,"async_setup"):
                setup_func = module.async_setup
            elif hasattr(module,"setup"):
                setup_func = module.setup

            if not isinstance(setup_func,Callable):
                _LOGGER.error(f"{integration} does not have a valid setup function, not importing")
                raise TypeError
            
            _LOGGER.info(f"Setting up integration {integration}")
            if progress_func:
                progress = progress + step
                progress_func(progress, f"Setting up integration {integration}")
            try:
                if asyncio.iscoroutinefunction(setup_func):
                    res = await setup_func(core ,config)
                else:
                    res = setup_func(core, config)

                if res == None:
                    _LOGGER.error(f"Integration setup functions must return a result (at minimum a boolean `True`), or `False`. {integration} returned `None`")
                    continue

                if res == False:
                    _LOGGER.error(f"Something went wrong setting up {integration}")
                    continue
                
                cls._loaded_integrations.add(Path(module.__file__).parent)
                if res != True:
                    integration_objects[integration] = res

                _LOGGER.debug(f"{integration} succesfully set up")
            except (ModuleNotFoundError, ImportError) as exce:
                msg = f"Error importing integration {integration}: {exce}. The integration may not be able to run in an emulated environment."
                _LOGGER.warning(msg)
            except Exception as exce:
                msg = f"Error importing integration {integration}: {exce}."
                _LOGGER.error(msg, exc_info=True)

        return MappingProxyType(integration_objects)    
    
    @classmethod
    async def async_start_integrations(cls, core: "CORE"):
        """
        Calls the setup functions for relevant integrations. If a maximum time was set in the config, will continue setting up in the background while inkBoard starts printing.

        Parameters
        ----------
        core : CORE
            The inkBoard core module
        """   

        cls._done_setups = {}
        cls._pending_setups = {}

        config = core.config

        coro_list = set()
        for integration, module in cls._imported_modules.items():
            pkg = module.__package__
            setup_res = core.integration_objects.get(integration,None)

            if hasattr(module, "async_start"):
                if not asyncio.iscoroutinefunction(module.async_start):
                    _LOGGER.error(f"integration {integration}: async_start must be a coroutine")
                    continue
                t = asyncio.create_task(module.async_start(core, setup_res), name=pkg)

            elif hasattr(module, "start"):
                coro = asyncio.to_thread(module.start, core, setup_res)
                t = asyncio.create_task(coro,name=pkg)
            else:
                continue

            coro_list.add(t)
            cls._pending_setups[pkg] = t

        if not coro_list:
            return
        
        setup_time = config.inkBoard["integration_start_time"]

        if setup_time < 0:
            await cls._wait_for_start(coro_list)
        else:
            setup_task = asyncio.create_task(cls._wait_for_start(coro_list))
            try:
                await asyncio.wait_for(asyncio.shield(setup_task), setup_time)
            except asyncio.TimeoutError:
                _LOGGER.warning(f"Integration setup time of {setup_time} seconds elapsed but not all integrations are setup yet. Integrations {cls._pending_setups.keys()} will continue setup in the background.")

        return
    
    @classmethod
    async def _wait_for_start(cls, coro_list):
        pending = coro_list 
        while pending:
            try:
                done, pending = await asyncio.wait(pending,return_when=asyncio.FIRST_COMPLETED)
            except:
                for t in done:
                    t : asyncio.Future
                    if t.cancelled():
                        continue

                    if t.exception() != None:
                        _LOGGER.error(f"Integrations {t.get_name()} ran into an error while starting up: {t.exception()}")
            else:
                names = set()
                for t in done:
                    names.add(t.get_name())
                _LOGGER.info(f"Integrations {names} were started.")
            finally:
                cls._pending_setups.pop(t.get_name())
                cls._done_setups[t.get_name()] = t

    @classmethod
    async def run_integrations(cls, core: "CORE"):
        """
        Runs any long running tasks defined by integrations.
        Exceptions do not interfere with the print loop.

        Parameters
        ----------
        core : CORE
            The inkBoard core module
        """
        coro_list = set()

        async def await_setup(pkg, runner : asyncio.Task):
            setup_task = cls._pending_setups.get(pkg,None)
            _LOGGER.warning(f"Waiting to start {pkg} long running task until its setup has finished.")
            if setup_task != None:
                await setup_task
                await asyncio.sleep(0)
            await runner

        for integration, module in cls._imported_modules.items():

            pkg = module.__package__
            setup_res = core.integration_objects.get(integration,None)

            if hasattr(module, "async_run"):
                if not asyncio.iscoroutinefunction(module.async_run):
                    _LOGGER.error(f"integration {pkg}: async_run must be a coroutine")
                    continue

                if pkg in cls._pending_setups:
                    coro = await_setup(pkg, module.async_run(core, setup_res))
                else:
                    coro = module.async_run(core, setup_res)

                t = asyncio.create_task(coro, name=pkg)
                coro_list.add(t)

        if not coro_list:
            return

        pending = coro_list
        ##From what I could find, this is the only way to catch out exceptions when they happen (gather only returns when everything is done, or returns a single result)
        ##While keeping a reference to the original task (which doesn't seem to happen for as_completed I believe) -> that only also just throws an exception

        done = []
        while pending:
            try:
                done, pending = await asyncio.wait(pending,return_when=asyncio.FIRST_COMPLETED)
            except:
                for t in done:
                    t : asyncio.Future
                    if t.cancelled():
                        _LOGGER.warning(f"Integration {t.get_name()} was cancelled while running.")

                    if t.exception() != None:
                        _LOGGER.error(f"Integration {t.get_name()} ran into an error while running: {t.exception()}")


