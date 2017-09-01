#!/bin/bash

cd $ORKA_HOME/testing/apps

while IFS= read -r PACKAGE; do
    # if directory and no debug app already
    if [ -d "$PACKAGE" ] && [ ! -f "$PACKAGE/${PACKAGE}_debug.apk" ]; then
        # decompile
        java -jar $ORKA_HOME/dependencies/apktool_2.2.0.jar d $PACKAGE/$PACKAGE.apk -o working/ --force
        # look for flag
        if grep -q 'android:debuggable=' working/AndroidManifest.xml
        then
            # if present, update flag
            sed -i '' -e 's/android:debuggable="false"/android:debuggable="true"/g' working/AndroidManifest.xml
        else
            # otherwise insert it
            sed -i '' -e 's/<application/<application android:debuggable="true"/g' working/AndroidManifest.xml
        fi
        # recompile
        java -jar $ORKA_HOME/dependencies/apktool_2.2.0.jar b working/ -o $PACKAGE/${PACKAGE}_debug.apk
        # sign
        jarsigner -keystore $ORKA_HOME/dependencies/debug.keystore $PACKAGE/${PACKAGE}_debug.apk androiddebugkey -storepass android
        rm -rf working
    fi
done < <(ls)
