import asyncio
import sys
import subprocess
import webbrowser
from logging import handlers as loghandlers

from inkBoard import logging, CORE
from inkBoard.async_ import create_reload_safe_task

from PythonScreenStackManager.pssm.decorators import elementactionwrapper
from PythonScreenStackManager.pssm import util

_LOGGER = logging.getLogger(__name__)

@elementactionwrapper
async def open_log_terminal(level = None):
    create_reload_safe_task(_open_log_terminal(level))

async def _open_log_terminal(level):

    proc_args = ["-m", "inkBoard", "logs"]

    sockethandler = logging.LocalhostSocketHandler(loghandlers.DEFAULT_TCP_LOGGING_PORT, level)
    exe = sys.executable
    exe = exe.replace("pythonw.exe", "python.exe")

    proc = await asyncio.create_subprocess_exec(exe, *proc_args, creationflags=subprocess.CREATE_NEW_CONSOLE)
    sockethandler.addToHandlers()

    try:
        await proc.wait()
    except Exception as exce:
        print(exce)
    finally:
        # log_task.cancel()
        sockethandler.close()
        try:
            if proc.returncode:
                proc.terminate()
        except ProcessLookupError:
            pass
        except:
            _LOGGER.exception("Something unexpected went wrong killing the log process")
    return

@elementactionwrapper
def open_config_folder(*args):
    
    if sys.platform == "win32":
        url = CORE.config.filePath
        subprocess.Popen(f'explorer /select,"{url}"')
    else:
        url = CORE.config.baseFolder ##Better to use the folder, using the file seemed to open it in vscode
        webbrowser.open("file:///" + str(folder))

    return