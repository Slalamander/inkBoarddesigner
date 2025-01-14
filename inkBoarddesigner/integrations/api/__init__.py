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
    from .server import inkBoardAPI

async def async_setup(core : "CORE", config : "CORE.config"):

    from .server import make_app

    app = make_app()
    app._core = core
    return app


async def async_run(core: "CORE", app : "inkBoardAPI"):
    app._server = app.listen(DEFAULT_PORT)
    return

def stop(core: "CORE", app : "inkBoardAPI"):

    app.server.stop()