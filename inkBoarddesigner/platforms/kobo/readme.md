
The kobo platform is what inkBoard (well, PSSM) was originally developed for. The installation is not too difficult, but does require installing software on your ereader. So be aware that this may, and likely will, void your warranty.

## Installation

### requirements:
    - A kobo device
    - An ssh client
    - Some command line knowledge

The installation process is written based on a factory reset Kobo Glo HD

 - Connect the device to your wifi network. This will be needed later on to get Python up and running.
 - Activate the device via the kobo servers (follow the instructions on the device). There should be ways to circumvent this, but that is outside the scope of this readme.
 - Navigate to: https://www.mobileread.com/forums/showthread.php?t=254214 \
Here you can download NiLuJe's package that allows installing python on the device.
 - Follow the instructions to install it as described by the post.
 - Connect to the device over ssh. If you need to find the IP address, you can go to `more -> settings -> device information` on your device, where the ip address is listed.
 - Follow the instructions in the Mobile Read post to install Python3 (Instruction here will resume from that step, however more are already indicated in the installation process itself)
 - Run `python-setup` in order to generate the Python bytecode
 - Create the folder `/mnt/onboard/.adds/inkBoard`. The provided script files assume this folder to hold the configuration etc. Set your terminal's directory to it: `cd /mnt/onboard/.adds/inkBoard`
 - Pip needs to be installed to take care of installing all requirements. Run `python3.9 -m ensurepip`. You should have seen the warning after compiling Python, so be sure that you want to continue. Mainly, if python is updated on the device, you will need to install inkBoard again. The packaging process, and installation in a virtual environment is partially meant to alleviate this.
 - Optionally add pip to path, but this is not required. If you want to, run `python3.9 -m pip install inkBoard`
 - Create the virtual environment: `python3.9 -m venv .venv --system-site-packages`. The `--system-site-packages` flag ensures the environment does have access to the packages already provided by the python package. Activate it by running `source ./.venv/bin/activate`.
 - Run `pip install inkBoard` to install inkBoard. Inside the environment, there is access to pip.
 - If you want to be able to invoke inkBoard without the python prefix (i.e. `inkBoard version` instead of activating the venv and then running `inkBoard version`), run the command `ln -sf /mnt/onboard/.adds/inkBoard/.venv/bin/inkBoard /usr/bin/inkBoard`. Check if it worked by running `inkBoard version`.
 - If you created a package, in the configuration folder or the base folder, there should be a script called `setup.sh`. If you run it, it should setup the setting to keep the wifi on as well, and include a script that will automatically start inkBoard when the device boots.



## Configuration

The base configuration is as follows:

```yaml
device:
  platform: kobo
```

All options to pass are:


| **Option**            | **Type** | **Description**                                                                                                                                                             | **Default**                        |
|-----------------------|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| `name`                | str      | The name to give the device in inkBoard                                                                                                                                     | The name as reported by the device |
| `rotation` | int, str | An fbink rotation string, or an integer between 0-3. Maps as follows: **"UR"**: 0, *upright*; **"CW"**: 1, *clockwise*; **"UD"**: 2, *upside down*; **"CCW"**: 3, *counter clockwise* | UR | 
| `kill_os`             | bool     | If `true`, this stops the running kobo layer when inkBoard boots. This does mean the device needs to be rebooted to get it back.                                            | `true`                             |
| `refresh_rate`        | str, int | The time between full screen refreshes. This gets rid of so called 'ghosting' on the E-ink screen. If the passed value if a float or integer, it is interpreted as seconds. | 30min                              |
| `touch_debounce_time` | str, int | time to wait for a touch to be considered valid.                                                                                                                            | 0.01                               |
| `hold_touch_time`     | str, int | Time to wait before considering a touch as a held touch                                                                                                                     | 0.5                                |
| `input_device_path`   | str      | Optional path to the input_device file on linux. Defaults to the default value found in the input library                                                                   | As set by the input lib            |

### Notes

Some notes and reminders regarding the installation process:

- To install pip run: `python3.9 -m ensurepip`
- To update pip run: `/mnt/onboard/.niluje/python3/bin/pip3.9 install -U setuptools pip`
- Symlinking pip into PATH: `ln -sf /mnt/onboard/.niluje/python3/bin/pip /usr/bin/pip`
- Due to a quirk in touch handling, in order to implement the hold functionality, the first touch is never registered as valid. 
- In case your device breaks, I was able to reset the firmware by holding the top button, and pressing both corners of the screen at the same time. This was on a Kobo Glod HD, and the process may differ on other devices.
