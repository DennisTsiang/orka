#!/bin/bash

POWER_PROFILE_PATH=$1

cd $ORKA_HOME/testing/apps

while IFS= read -r line; do
    if [ -d "$line" ]; then
        python petra_config_helpers.py $line $POWER_PROFILE_PATH
    fi
done < <(ls)

