"""A module with two small functions to use as examples for custom functions.

Use by requesting a function using 'custom:{function_name}'
"""

from typing import TYPE_CHECKING

from PythonScreenStackManager.pssm.util import elementactionwrapper
from PythonScreenStackManager.elements import Button
from PythonScreenStackManager.pssm_types import InteractEvent

from inkBoard import core as CORE


if TYPE_CHECKING:
    from inkBoard.integrations.homeassistant_client import client

def my_function(elt: Button, interaction: InteractEvent):
    """A very basic custom function.

    Attach it as a tap_action to a Button element. When tapped, its text will to display the touched coordinates.
    """
    (x,y, _) = interaction
    elt.update({"text": f"You touched coordinates {(x,y)}"})

@elementactionwrapper
def my_print_function():
    """A basic custom function using the `elementactionwrapper` decorator.
    
    This decorator wraps a function to catch a function call and removes the element and touch event, provided those are the only two positional arguments.
    Aside from that, it also shows how to interface  with the inkBoard core, which holds the core components for a running config.
    This includes, for example, the screen instance, a dict with all integrations, and as can be seen below, the device instance.
    """
    network = CORE.device.network.SSID
    print(f"Connected to {network}")

def custom_trigger(trigger: "client.triggerDictType", client: "client.HAclient"):
    """A simple function to show how to work with trigger functions for home assistant entities.

    Parameters
    ----------
    trigger : client.triggerDictType
        _description_
    client : client.HAclient
        _description_
    """
    
    entity = trigger["entity_id"]
    new_state = trigger["to_state"]["state"]

    if trigger["from_state"] == None:
        ##from_state is none if the client connected, as it does not gather the previous state of the entity, just the current state.
        print(f"Entity {entity} is in state {new_state}")
    else:
        ##Although it prints it like this, keep in mind the function is triggered regardless of what triggered it.
        ##I.e. it can also be the case that the trigger was caused by an attribute changing.
        from_state = trigger["from_state"]["state"]
        print(f"Entity {entity} changed to state {new_state} from state {from_state}")
    return