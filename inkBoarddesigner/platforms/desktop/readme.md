## inkBoard Desktop

The desktop implementation is the most basic platform to run inkBoard on. Most likely you're familiar with it, as it forms the basis of the emulator as well. However, a lot of options that are guarded off by the emulator are available here.

## Installation

If running this on a machine where the designer is not installed, and it is not desired to do so, you can follow this process. Otherwise, follow the documentation to install the designer.
Ensure you have a compatible Python version installed (likely 3.9 or 3.10), and run
```console
pip install inkBoard
```

## Usage

The most basic configuration for this platform is as follows:

```yaml
device:
  platform: desktop
```

With the following options being allowed for the configuration:

| Option            | Type | Description                                                                                                                                                                    | Default  |
|-------------------|------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| `name`            | str  | The name of the device                                                                                                                                                         | `None`   |
| `frame_rate`      | int  | The amount of times the window is updated per second (i.e. fps).  Does not need to be incredibly high for simple dashboards.                                                   | 20       |
| `width`           | int  | The width of the window, in pixels                                                                                                                                             | 1280     |
| `height`          | int  | The height of the window, in pixels                                                                                                                                            | 720      |
| `fullscreen`      | bool | Whether to start inkBoard in fullscreen mode.  Setting this to `true` means whatever is passed to `width` and `height` is ignored.                                             | `false`  |
| `resizable`       | bool | Allows the window to be resized by dragging on the edges                                                                                                                       | `false`  |
| `cursor`          | str  | The cursor type to use, must be a tkinter applicable value. See [here](https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/cursors.html) for availables types.                                                                                 | target   |
| `interactive`     | bool | Whether to run in interactive mode (i.e. allowing inputs on the dashboard)                                                                                                     | `true`   |
| `network`         | bool | Allow the device to poll the network. If installed, may allow for managing the connection too.                                                                                 | `true`   |
| `backlight`       | bool | Puts a semi transparent rectangle over the dashboard, simulating a backlight.                                                                                                  | `false`  |
| `backlight_alpha` | bool | The maximum allowed opacity of the backlight rectangle. The higher the value, the darker the dashboard will be when the backlight is off.                                      | 175      |
| `window_icon`     | str  | An icon to use as the window's icon. Must be .ico file. On windows, the taskbar icon does not reflect this icon due to how it groups programmes. Default is the inkBoard icon. | inkBoard |

So a simple dashboard that is just a small window on your desktop could look like this:

```yaml
device:
  platform: desktop
  width: 480
  height: 360
```

Features present in the config are settable. Aside from that, if interactive is `true`, the device supports the 'hold_release' function, meaning elements can have `tap_action`, `hold_action` and `hold_release_action` defined.