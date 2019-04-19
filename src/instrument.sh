#!/bin/bash

# Generate an injected, signed APK file from an initial APK.
#
# usage: ./instrument.sh apkfile outdir pdir
# apkfile -- file to inject
# outdir -- output directory for the smali files
# pdir -- relative path of the package directory within the smali directory
#
# injected apk is located at outdir/dist/orka.apk

APKFILE=$1
OUTDIR=$2
PDIR=$3

APKTOOL=$ORKA_HOME/dependencies/apktool_2.4.0.jar
LOGGER=$ORKA_HOME/dependencies/Logger.smali
KEYSTORE=$ORKA_HOME/dependencies/debug.keystore

ORKA_APK=$OUTDIR/dist/orka.apk

# check that target file exists
if ! [ -e $APKFILE ]
    then
        echo "Cannot find apk $APKFILE, please check the path."
        exit
fi

# decompile with ApkTool, the -f will clear the $OUTDIR directory
java -jar $APKTOOL d $APKFILE -o $OUTDIR/ --no-res --force

echo "OUTDIR: $OUTDIR"
echo "PDIR: $PDIR"
cd $OUTDIR
find_paths=()

# Store result of find command into array
mapfile -t find_paths < <(find -wholename "*$PDIR*" | cut -d'/' -f2)

# Remove duplicates from array
smali_folders=($(printf "%s\n" "${find_paths[@]}" | sort -u))

# add logger smali file
cp $LOGGER $OUTDIR/${smali_folders[0]}/$PDIR/Logger.smali

for smali_folder in "${smali_folders[@]}"
do
  # inject application
  python $ORKA_HOME/src/inject.py $OUTDIR/$smali_folder/$PDIR/
done

#check the .smali1 code exists
if ls "$OUTDIR/${smali_folders[0]}/$PDIR/*.smali.orkatmp" 1> /dev/null 2>&1;
    then
        echo "Cannot find the instrumented files please make sure the injector ran correctly"
        exit
fi

java -jar $APKTOOL empty-framework-dir --force
# recompile application
java -jar $APKTOOL b $OUTDIR/ -o $ORKA_APK

# sign application
jarsigner -keystore $KEYSTORE $ORKA_APK androiddebugkey -storepass android
