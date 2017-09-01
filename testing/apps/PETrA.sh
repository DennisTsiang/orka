#!/bin/bash

cd $ORKA_HOME/testing/apps

APP_NAME=$1
NRUNS=$2

for i in `seq 1 $NRUNS`;
    do
        cp $ORKA_HOME/testing/monkey_playback.py $ORKA_HOME/dependencies/monkey_playback.py
        java -jar $ORKA_HOME/dependencies/PETrA.jar --batch $APP_NAME/config.properties
        mv $APP_NAME/petra_results/run_1 $APP_NAME/petra_results/run$i
    done

java -jar $ORKA_HOME/dependencies/PETrAPostProcessor.jar $APP_NAME/petra_results;
sed -i -e "s/$APP_NAME.//g" $APP_NAME/petra_results/routineCosts.csv;
rm $APP_NAME/petra_results/routineCosts.csv-e
