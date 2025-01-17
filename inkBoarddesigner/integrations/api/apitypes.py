from typing import TypedDict, Union, Literal

class removeaccessdict(TypedDict):
    actions: list[str]
    action_groups: list[str]
    group_actions: dict[str,list[str]]


class baseconfig(TypedDict):
    name: str
    "Name of the inkBoard instance"

    start_time: str
    "The time at which the instances was started, in isoformat"

    platform: str
    "The platform inkBoard is running on"

    version: str
    "The inkBoard version"

    integrations: list
    "The integrations imported for the instance"


class _mainelement(TypedDict):
    id: str
    "The main element's id"

    type: str
    "The type of the element"

    tabs: list
    """The available tabs
    Only present if the element is (based on) TabPages
    """

    current_tab: str
    """The tab currently being shown
    Only present if the element is (based on) TabPages
    """

class _popups(TypedDict):
    current_popup: Union[str,None]
    "The current popup on screen, if any"

    registered_popups: list[str]
    "All the popups registered with the screen"

class restconfig(baseconfig):
    main_element: Union[_mainelement,None]
    "Configuration and state of the main element"

    popups: _popups
    "Information on the current popup and all registered popups"


class deviceconfig(TypedDict):

    platform: str
    "The device's platform"

    model: Union[str,None]
    "The device's model, if reported"

    name: Union[str,None]
    "Name of the device"

    size: tuple[int,int]
    "The size of the device's screen or printable area"

    screen_type: Union[str, None]
    "The type of device's screen, if reported"

    screen_mode: str
    "The image mode of the eventual images being printed"

    rotation: Union[str,None]
    "The current rotation of the device. None if it is not a supported feature"

    features: list[str]
    "The features of the device"

class batteryconfig(TypedDict):
    state: Literal["full","charging","discharging"]
    "Battery state"

    charge: int
    "Battery charge level, from 0-100"

class networkconfig(TypedDict):

    ip_address: str
    "The current ip address of the device"

    mac_address: str
    "The mac address of the device's network adapter"

    network_ssid: str
    "The SSID of the network the device is connected to"

    signal: Union[None, int]
    "The network's signal strength from 0-100, if reported."

class backlightconfig(TypedDict):

    state: bool
    "State of the backlight, true for on, false for off"

    brightness: int
    "The brightness of the backlight, from 0-100"

    behaviour: Literal['Manual', 'On Interact', 'Always']
    "The behaviour of the backlight"

    default_time_on: Union[int,float,str]
    "The default on time for the backlight, for temporary turn on"

    default_brightness: int
    "The default brightness to turn on the backlight with if none is configured"

    default_transition: float
    "The default transition time in seconds"

class actionsconfig(TypedDict):

    shorthands: list[str]
    "The shorthand actions available to the api"

    groups: list[str]
    "The shorthand action identifiers available to the api"

    