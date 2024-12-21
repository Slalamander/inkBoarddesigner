
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
 - Enable the option to keep wifi on. Click the search icon and type `devmodeon`. If you then navigate to `more -> settings -> device information`, you should see an option called `Developer options`. Open it and enable `Force Wifi ON`.
 - Connect to the device over ssh. If you need to find the IP address, you can go to `more -> settings -> device information` on your device, where the ip address is listed.
 - Follow the instructions in the Mobile Read post to install Python3 (Instruction here will resume from that step, however more are already indicated in the installation process itself)
 - Run `python-setup` in order to generate the Python bytecode
 - Pip needs to be installed to take care of installing all requirements. Run `python3.9 -m ensurepip`. You should have seen the warning after compiling Python, so be sure that you want to continue. Mainly, if python is updated on the device, you will need to install inkBoard again. The packaging process, and installation in a virtual environment is partially meant to alleviate this. If you want to, you can add pip to path as instructed by the output of the previous command. However this is not required if you are only going to be working with inkBoard packages.
 - Create the folder `/mnt/onboard/.adds/inkBoard`. The provided script files assume this folder to hold the configuration etc. Set your terminal's directory to it: `cd /mnt/onboard/.adds/inkBoard`
 - Create a virtual environment that will hold all inkBoard related packages: `python3.9 -m venv .venv --system-site-packages`. The `--system-site-packages` flag ensures the environment does have access to the packages already provided by the python package. Activate it by running `source ./.venv/bin/activate`.
 - Run `pip install inkBoard` to install inkBoard. Inside the environment, there is access to pip.
 - Add the inkBoard command to the path, to be able to invoke inkBoard without the python prefix (i.e. `inkBoard version` instead of activating the venv and then running `inkBoard version`), run the command `ln -sf /mnt/onboard/.adds/inkBoard/.venv/bin/inkBoard /usr/bin/inkBoard`. Check if it worked by running `inkBoard version`.
 - If you created a package, you can run `inkBoard install` in the folder. This should identify the package and take you through the steps to install it. After that, the configuration folder should be unpacked too. In the `files` folder there should be a script called `setup_auto_start.sh`. This will copy the file `init_script` to `/etc/init.d` and add to the commands to run at boot. The script calls `auto_start.sh` 60 seconds after booting up, which runs inkBoard. By default, it runs the file "configuration.yaml", but the filename can be changed in `kobo_settings.json`. The "auto_start" entry in there can also be changed if automatically starting inkBoard is not desired anymore. If desired, First run `dos2unix ./files/init_script`, this is needed in case the init_script was edited in windows, which tends to break it. Run the setup script via `./files/setup_auto_start.sh`. (If you want to see if it worked, run `/etc/init.d/inkboard_boot`. It should output `Starting inkBoard in 60 seconds...` after which you can cancel it by pressing ctrl+c)
 - You can now run inkBoard via the usual command line interface, i.e. `inkBoard run configuration.yaml`.

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
- If preffered, the setup script can encompass every step after installing python on the device. However due to the notes and stuff in it, I do think it is better to have people just follow the readme entirely, so they also have an idea of how to maybe fix stuff if it breaks.
