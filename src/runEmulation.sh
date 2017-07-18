#!/bin/bash

# Run a monkeyrunner script on an injected apk to collect energy usage raw data.
#
# Arguments:
# apk -- path to the injected apk
# package_name -- application's package name (see main.getPackageInfo)
# component_name -- application's component name (see main.getPackageInfo)
# avd -- name of the emulator
# monkey -- path to the monkeyrunner script
# monkey_input -- input for the monkeyrunner script
# nruns -- number of time the script should be executed

APK=$1
PACKAGE_NAME=$2
COMPONENT_NAME=$3
AVD=$4
MONKEY=$5
MONKEY_INPUT=$6
NRUNS=$7

PORT=5554
ADB=$ANDROID_HOME/platform-tools/adb

# create or clear output directory if needed
OUTDIR=$ORKA_HOME/results_$AVD
if [ ! -d "$OUTDIR" ]; then
    mkdir $OUTDIR
fi

OUTDIR=$OUTDIR/$PACKAGE_NAME
if [ -d "$OUTDIR" ];
    then
        rm -rf $OUTDIR/*
    else
        mkdir $OUTDIR
fi


# load the emulator
# -wipe-data option reset user data on device
DEVICES=$($ADB devices | grep 'device\b')
if [ -z $DEVICES ];
    then
        $ANDROID_HOME/tools/emulator -avd $AVD -port $PORT -wipe-data &
fi

# wait for the device to boot
$ADB wait-for-device
while true;do
    LOADED=$($ADB shell getprop sys.boot_completed | tr -d '\r')
    if [ "$LOADED" = "1" ];
        then
            break
        else
            sleep 1
    fi
done

# uninstall any previous version of APK
$ADB uninstall $APK
# install the APK
$ADB install $APK
# get app uid
APPUID=$($ADB shell dumpsys package $PACKAGE_NAME | grep -oP '(?<=userId=)\S+')
echo $APPUID > $OUTDIR/appuid

# disable ac charging
$ADB shell dumpsys battery set ac 0

#unlock screen
$ADB shell input keyevent 82

for i in `seq 1 $NRUNS`;
    do
        RUNDIR=$OUTDIR/run_$i
        mkdir $RUNDIR

        LOGCAT=$RUNDIR/logcat.txt
        BATTERYSTATS=$RUNDIR/batterystats.txt

        # reset logcat
        $ADB logcat -c

        # start dumping log
        $ADB logcat -v thread orka:I *:S > $LOGCAT &
        LOGCAT_PID=$!

        # reset battery stats and disable usb charging
        $ADB shell dumpsys battery set usb 1
        $ADB shell dumpsys battery set usb 0
        sleep 1

        #run monkey script
        $ANDROID_HOME/tools/bin/monkeyrunner $MONKEY $COMPONENT_NAME $MONKEY_INPUT

        # wait for execution to fully terminate
        sleep 5

        # stop dumping log
        kill $LOGCAT_PID
        # dump battery stats
        $ADB shell dumpsys batterystats --unplugged > $BATTERYSTATS
        # stop app and clear app data
        $ADB shell pm clear $PACKAGE_NAME
    done

# uninstall the APK
$ADB uninstall $PACKAGE_NAME

# reset usb charging
$ADB shell dumpsys battery set usb 1

# kill emulator if it was booted by orka
if [ -z $DEVICES ];
    then
        $ADB emu kill
fi
