"Takes care of handling and setting the settings for the designer."

import logging
from pathlib import Path
from configparser import ConfigParser
from . import const 

logger = logging.getLogger(__name__)

EM_SETTINGS_FILE = Path(__file__).parent / "files" / "settings.ini"
"json file to save the emulator settings to."

DEFAULT_EM_SETTINGS = {
                    const.DARKMODE_VAR_NAME: False, 
                    const.SAVEAS_VAR_NAME: False, 
                    const.HIGHLIGHT_VAR_NAME: False, 
                    const.LIST_VAR_NAME: "None", 
                    "backlight": False, 
                    "battery_rnd": False, 
                    "network": False}
"The default settings to use when the settings file cannot be opened"

_section = "SETTINGS"
"Section for using EM_SETTING.get(SEC) (So you don't need to write SETTINGS each time.)"

EM_CONFIG = ConfigParser(DEFAULT_EM_SETTINGS, default_section=_section)
EM_CONFIG.read(EM_SETTINGS_FILE)

EM_SETTINGS = EM_CONFIG["SETTINGS"]
"Settings used for the emulator. Saved between sessions."

#Add a section per platform to keep settings for it

def save_settings():
    "Save the emulator settings to the settings file"
    logger.debug("Saving emulator settings")
    with open(EM_SETTINGS_FILE, 'w') as configfile:
        EM_CONFIG.write(configfile)