"Api integration for inkBoard"

from typing import *

if TYPE_CHECKING:
    from inkBoard import core as CORE
    from .app import APICoordinator

async def async_setup(core : "CORE", config : "CORE.config"):

    ##Somehow make a check to see if the device has network access
    ##That would require setup to happen after the device is created, may be possible though?

    from .app import APICoordinator


    conf = config["api"]
    if conf in {None, ""}: conf = {}

    apiapp = APICoordinator(core, **conf)

    return apiapp


async def async_run(core: "CORE", app : "APICoordinator"):
    await app.listen()
    return

def stop(core: "CORE", app : "APICoordinator"):
    app.stop()

##Considerations for platforms:
##Opted for tornado for lack of requirements and it being quite barebones
##In the end speed is not a priority for inkBoard
##Benchmarks for apis: https://github.com/klen/py-frameworks-bench

##encryption/token authentication:
##Will not implement it MYSELF.
##In this case, I am quite sure it is better to not have it and provide an adequate warning
##Instead of implementing it and giving users a false sense of protection.
##Authentication is likely doable by just setting a key, but encryption I'm not as sure
