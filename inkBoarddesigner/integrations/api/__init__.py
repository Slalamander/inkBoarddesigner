"Api integration for inkBoard"

##Considerations for platforms:

# Async:
## - FastAPI: has a lot of dependencies, not sure. Also many bells and whistles that should not be required for inkBoard
## - Sanic: seems great but requires uv, which uses cyton, meaning it cannot be installed on kobo -> off the table
## - Falcon: both pure python and cython, no dependencies (not fully true, but depends on implementation)
## - tornado: relatively lowlevel
## - aiohttp: seems to be cython based? Otherwise the distribution on pypi is 8mb

#Synchronous
## - Flask

##Will try out with tornado. Not the fastest (relatively slow even), but considering it is a minor endpoint that should not handle much that is not a major problem I hope.
##Benchmarks for apis: https://github.com/klen/py-frameworks-bench

from typing import *

from .constants import DEFAULT_PORT

if TYPE_CHECKING:
    from inkBoard import core as CORE
    from .server import inkBoardAPIServer

async def async_setup(core : "CORE", config : "CORE.config"):

    from .server import make_app

    ##For the config: allow manually omitting services etc. as well
    ##Also add a way to omit specific actions from a group

    app = make_app()
    app._core = core
    return app


async def async_run(core: "CORE", app : "inkBoardAPIServer"):
    app._server = app.listen(DEFAULT_PORT)

    ##To allow extensions e.d. to not have their functions available via the api:
    ##Add a property that lists the group and one for functions
    ##api should catch them out.
    return

def stop(core: "CORE", app : "inkBoardAPIServer"):

    app.server.stop()