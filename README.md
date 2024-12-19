![inkBoard Designer Logo](https://raw.githubusercontent.com/Slalamander/inkBoarddesigner/cf56abe61008b3364d179e9ebc3719c165555c65/assets/designer_logo.svg)

inkBoard Designer is meant to help designing inkBoard dashboards. While working on the software, it could be rather cumbersome trying to test code or dashboards on the platform itself. The designer provides an emulator, so it allows using the same yaml config as you'd use on device within it (as opposed to when you'd run it on the desktop platform). The interface is also meant to aid some steps in the design/install process.

For example, to keep the inkBoard package itself at a minimum, the platforms and integrations will be distributed along with the designer. However, it allows for creating packages of the running configuration, which can easily be installed in an inkBoard installation using `inkBoard install`.

## Installation

`pip install inkBoarddesigner`

## Usage

The command to run the designer is included in inkBoard itself, as well as some other hooks into it. It can be started by running `inkBoard designer`. Optionally, provide a configuration file to run, but that is not required. They can also be opened from the UI.

While I work on the documentation, the UI will likely be one of the last things to be written. For the moment, each widget has tooltips attached which should hopefully explain what they do adequately.

## Getting Started
Currently, two examples are included in the example folder. They are a good way to get started, and comments are included in the files to help explain what certain lines do. If you want to download just the example, you can do so via i.e. here: https://downgit.github.io/#/home

In the `examples/custom/integrations` folder, the `dummy_integration` is also included. This is a template/explanatory integration, with comments to somewhat explain what functions are required, what stuff does, etc. It can be included by using the `dummy_integration` entry in your config. Aside from that, the custom folder also includes examples for custom functions and custom elements, which are used by the example configurations as well.

For the Home Assistant example, you should fill out the `ha_substitutions.yaml` file. It currently all references to `secrets.yaml` (via the `!secret` anchor), but they can also be put in the file directly. To run the integration, you should run `inkBoard install integration homeassistant_client` first, which takes care of downloading the appropriate requirements (the `websockets` and `requests` packages.)

Running the examples can be done by selecting the yaml file from the designer ui, or running `inkBoard designer configuration.yaml` from the examples folder.

