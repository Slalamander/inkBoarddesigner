"""
This module (will) serve as an extension to the actual inkBoard module.
The designer is meant to help design and create inkBoard packages, for example provide an interface to "debug" your dashboard, but also hold the functionality to create e.g. standalone executables.
This way, the inkBoard module itself should be able to stay at a relatively small size, which should hopefully make it more portable.
"""
__version__ = "0.1.4"

from typing import TYPE_CHECKING
import logging
import asyncio
import threading
import sys

from . import const

if TYPE_CHECKING:
    import argparse

_LOGGER = logging.getLogger(__package__)

def check_threads() -> None:
    """Check if there are any lingering threads.

    From the HA source code
    """
    try:
        nthreads = sum(
            thread.is_alive() and not thread.daemon for thread in threading.enumerate()
        )
        if nthreads > 1:
            sys.stderr.write(f"Found {nthreads} non-daemonic threads.\n")

    except AssertionError:
        sys.stderr.write("Failed to count non-daemonic threads.\n")


def run_designer(args):
    """
    Runs inkBoard designer and builds the window

    Parameters
    ----------
    args : _type_
        Command line arguments
    """    

    ##Make base config and dashboard config into singleton classes
    ##At least take out the classs structure as it allows for more flexibility
    ##Also, don't forget to call the reload function when pressing the quit button

    ##Also don't forget, when running a new config to i.e. rebuild the icons and stuff

    from .runners import async_run_designer, async_stop_designer
    from inkBoard import logging as ib_logging

    ib_logging.init_logging()

    try:
        asyncio.run(async_run_designer(args))
    except KeyboardInterrupt:
        try:
            asyncio.run(async_stop_designer())
        except:
            pass

    check_threads()
    return 0


def _add_parser(parser: "argparse._SubParsersAction", name: str):
    designer_parser: "argparse.ArgumentParser" = parser.add_parser(name, 
                    description="Run inkBoard in designer mode, meant for desktop environments. Allows for designing dashboards without being limited by the platform it will run on, but with emulation capabilities to make performance as close as possible to what it will be on device. Requires inkBoarddesigner to be installed",
                    help="Runs inkBoard in designer mode", add_help=True)
    
    designer_parser.add_argument(const.ARGUMENT_CONFIG, nargs="?",
                                help="The YAML file used for the dashboard", default=None)

    return