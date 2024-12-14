#! /bin/sh


# Start from our working directory
cd "${0%/*}" || exit 1


# Siphon a few things from nickel's environment
#eval "$(xargs -n 1 -0 <"/proc/$(pidof nickel)/environ" | grep -e DBUS_SESSION_BUS_ADDRESS -e NICKEL_HOME -e WIFI_MODULE -e LANG -e WIFI_MODULE_PATH -e INTERFACE 2>/dev/null)"
eval "$(xargs -n 1 -0 <"/proc$(pidof nickel)/environ" | grep -e DBUS_SESSION_BUS_ADDRESS -e NICKEL_HOME -e WIFI_MODULE -e LANG -e WIFI_MODULE_PATH -e INTERFACE 2>/dev/null)"
export DBUS_SESSION_BUS_ADDRESS NICKEL_HOME WIFI_MODULE LANG WIFI_MODULE_PATH INTERFACE

# Now a few other things for wifi
PLATFORM="freescale"
if dd if="/dev/mmcblk0" bs=512 skip=1024 count=1 | grep -q "HW CONFIG"; then
    CPU="$(ntx_hwconfig -s -p /dev/mmcblk0 CPU 2>/dev/null)"
    PLATFORM="${CPU}-ntx"
fi

if [ "${PLATFORM}" != "freescale" ] && [ ! -e "/etc/u-boot/${PLATFORM}/u-boot.mmc" ]; then
    PLATFORM="ntx508"
fi
export PLATFORM

# add the option to not kill the wifi (from yawk) (not in use right now as it just keeps adding the option)
# echo >> "/mnt/onboard/.kobo/Kobo/Kobo eReader.conf"
# echo "[DeveloperSettings]" >> "/mnt/onboard/.kobo/Kobo/Kobo eReader.conf"
# echo "ForceWifiOn=true" >> "/mnt/onboard/.kobo/Kobo/Kobo eReader.conf"

# Flush the disks: might help avoid damaging nickel's DB...
sync

##Stop possible running inkboard instances

# Stop kobo software because it's running
fbink -k
killall nickel hindenburg sickel fickel fmon > /dev/null 2>&1


