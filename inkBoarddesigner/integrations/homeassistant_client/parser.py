
from inkBoard import core as CORE
from inkBoard.core import util

from . import HAelements, clientelements

d_HA = util.get_module_elements(HAelements)
d_client = util.get_module_elements(clientelements)

element_dict = d_HA | d_client #dict with all elements of the Home Assistant integration

def parse_ha_element(elt_type : str):
    return element_dict.get(elt_type,None)


# CORE.add_element_parser("HA",parse_ha_element)

def setup_elements():
    clientelements.HomeAssistantMenu()
    clientelements.menu.StatusBar.add_statusbar_element("home-assistant",clientelements.ClientElement())
