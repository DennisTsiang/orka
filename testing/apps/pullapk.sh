#!/bin/bash

cd $ORKA_HOME/testing/apps

PACKAGE=$1
mkdir $PACKAGE
cd $PACKAGE
adb pull /data/app/$PACKAGE-1/base.apk
mv base.apk $PACKAGE.apk

