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
AVD=$3
SCRIPT_CMD=$4
NRUNS=$5
PORT=$6
METHOD=$7
PICKLE=$8

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

USING_EMULATOR="false"

# check whether physical devices connected
DEVICES=$($ADB devices | grep 'device\b' | grep -v 'emulator')
# load the emulator if needed
# -wipe-data option reset user data on device
if [ -z "$DEVICES" ];
    then
        DEVICES=$($ADB devices | grep emulator-$PORT)
        if [ -z "$DEVICES" ]; then
          $ANDROID_HOME/tools/emulator -avd $AVD -port $PORT -no-boot-anim -no-snapshot-save -snapshot testsong &
        fi
        USING_EMULATOR="true"
fi

EMULATOR_SERIAL="0"
ADB_PREFIX=""
if [ "$USING_EMULATOR" = "true" ];
    then
        EMULATOR_SERIAL="emulator-$PORT"
        ADB_PREFIX="$ADB -s emulator-$PORT"
        if [ "$METHOD" = "Monkeyrunner" ];
          then
            SCRIPT_CMD="$SCRIPT_CMD $PORT"
        fi
else
        ADB_PREFIX="$ADB"
fi
echo "PORT: $6"
echo "ADB_PREFIX: $ADB_PREFIX"

# wait for the device to boot
$ADB_PREFIX wait-for-device

while true;do
    LOADED=$($ADB_PREFIX shell getprop sys.boot_completed | tr -d '\r')
    if [ "$LOADED" = "1" ];
        then
            break
        else
            sleep 1
    fi
done

# uninstall any previous version of APK
$ADB_PREFIX shell pm uninstall $APK
# install the APK
$ADB_PREFIX install $APK
# get app uid
APPUID=$($ADB_PREFIX shell dumpsys package $PACKAGE_NAME | grep -oP '(?<=userId=)\S+' | head -n 1)
echo "APPUID: $APPUID"
echo $APPUID > $OUTDIR/appuid

# disable ac charging
$ADB_PREFIX shell dumpsys battery set ac 0

#unlock screen
$ADB_PREFIX shell input keyevent 82

for i in `seq 1 $NRUNS`;
    do
        RUNDIR=$OUTDIR/run$i
        mkdir $RUNDIR

        LOGCAT=$RUNDIR/logcat.txt
        BATTERYSTATS=$RUNDIR/batterystats.txt
        NETSTATS=$RUNDIR/netstats.txt
        RUNTIMETXT=$RUNDIR/runtime.txt
        echo "NETSTATS: $NETSTATS"

        # reset logcat
        $ADB_PREFIX logcat -c

        # Start ACVTool to get statement coverage
        # -q flag starts in the background
        if [ -n "$PICKLE" ]; then
          echo "Starting ACV"
          acv start $PACKAGE_NAME -q -d $EMULATOR_SERIAL
          sleep 1
        fi
        # start dumping log
        # only outputs logs with tag orka at priority "info"
        #$ADB_PREFIX logcat -v threadtime orka:I *:S > $LOGCAT &
        $ADB_PREFIX logcat -v threadtime orka:I AndroidRuntime:E *:S> $LOGCAT &
        LOGCAT_PID=$!
        # start monitoring traffic. & makes it run in the background
        python $ORKA_HOME/src/netstatsMonitor.py -o $NETSTATS -i $APPUID -e $EMULATOR_SERIAL &
        NETSTATS_PID=$!

        # reset battery stats and disable usb charging
        $ADB_PREFIX shell dumpsys batterystats --reset
        $ADB_PREFIX shell dumpsys battery set usb 1
        $ADB_PREFIX shell dumpsys battery set usb 0
        sleep 1

        #run script command
        echo $SCRIPT_CMD
        START=`date +%s`
        $SCRIPT_CMD
        END=`date +%s`
        RUNTIME=$((END-START))
        echo $RUNTIME > $RUNTIMETXT

        # wait for execution to fully terminate
        sleep 4

        # stop dumping log and monitoring traffic
        kill $LOGCAT_PID
        kill $NETSTATS_PID

        # dump battery stats
        $ADB_PREFIX shell dumpsys batterystats --charged > $BATTERYSTATS

        # generate statement coverage report
        if [ -n "$PICKLE" ]; then
          acv stop $PACKAGE_NAME -d $EMULATOR_SERIAL -t 10
          acv report -p $PICKLE -o $OUTDIR -html $PACKAGE_NAME
        fi

        # stop app and clear app data
        $ADB_PREFIX shell pm clear $PACKAGE_NAME
    done

# uninstall the APK
$ADB_PREFIX uninstall $PACKAGE_NAME

# reset usb charging
$ADB_PREFIX shell dumpsys battery set usb 1

# kill emulator if it was booted by orka
if [ -z "$DEVICES" ];
    then
        $ADB_PREFIX emu kill
fi
