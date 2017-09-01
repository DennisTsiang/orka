#!/bin/bash

cd $ORKA_HOME/testing/apps

while IFS= read -r line; do
    if [ -d "$line" ]; then
        cp ../lv_test_scripts/$line.txt $line/
    fi
done < <(ls)

