#!/bin/sh

cd "$(dirname "$0")"

SETTINGS_FILE="kobo_settings.json"
AUTO_START=$(jq ".auto_start" "$SETTINGS_FILE")
CONFIG_FILE=$(jq -r ".config_file" "$SETTINGS_FILE")

if $AUTO_START; then
    cd "../"
    inkBoard run $CONFIG_FILE
fi