# inkBoard Designer

inkBoard Designer is meant to help designing inkBoard dashboards. While working on the software, it could be rather cumbersome trying to test code or dashboards on the platform itself. The designer provides an emulator, so it allows using the same yaml config as you'd use on device within it (as opposed to when you'd run it on the desktop platform). The interface is also meant to aid some steps in the design/install process.

For example, to keep the inkBoard package itself at a minimum, the platforms and integrations will be distributed along with the designer. However, it allows for creating packages of the running configuration, which can easily be installed in an inkBoard installation using `inkBoard install`.

## Installation

`pip install inkBoarddesigner`

## Usage

The command to run the designer is included in inkBoard itself, as well as some other hooks into it. It can be started by running `inkBoard designer`. Optionally, provide a configuration file to run, but that is not required. They can also be opened from the UI.

While I work on the documentation, the UI will likely be one of the last things to be written. For the moment, each widget has tooltips attached which should hopefully explain what they do adequately.
