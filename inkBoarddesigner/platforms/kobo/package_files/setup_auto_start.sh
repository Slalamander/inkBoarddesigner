#!/bin/sh

# APP_FOLDER="/mnt/onboard/.apps/yawk/"
# INIT_SCRIPT_LOCAL="$APP_FOLDER/utils/init_script"
# INIT_SCRIPT_REMOTE="/etc/init.d/yawk"

INITD_NAME="inkboard_boot"
APP_FOLDER="/mnt/onboard/.adds/inkBoard"
# INIT_SCRIPT_LOCAL="$APP_FOLDER/init_script"
INIT_SCRIPT_LOCAL="$APP_FOLDER/files/init_script"
INIT_SCRIPT_REMOTE="/etc/init.d/$INITD_NAME"

if [ ! -d $APP_FOLDER ]; then
    echo "Please move the application to the correct folder: $APP_FOLDER"
    exit -1
fi

if [ ! -e "$INIT_SCRIPT_LOCAL" ]; then
    echo "The init script 'init_script' does not exist."
    exit 1
fi

if [ -e "$INIT_SCRIPT_REMOTE" ]; then
    echo "A file at the init script location $INIT_SCRIPT_REMOTE already exists."
    exit 1
fi

cd $APP_FOLDER

dos2unix $INIT_SCRIPT_LOCAL

# copy the automatic initializer
cp $INIT_SCRIPT_LOCAL $INIT_SCRIPT_REMOTE
chmod a+x $INIT_SCRIPT_REMOTE

# check if inittab already contains the rcS2 command -> since the file is checked for though, it is unlikely that this will be true
if grep -q "$INITD_NAME" /etc/inittab; then
    # delete the line containing the rcS2 command
    sed -i "/$INITD_NAME/d" /etc/inittab
fi
# add the command to start the yawk
echo "::sysinit:/etc/init.d/$INITD_NAME" >> /etc/inittab

echo
echo "All good! After rebooting the device, inkBoard should start automatically. Edit ./files/kobo_settings.json to change the behaviour."