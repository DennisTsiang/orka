#!/usr/bin/env python

""""Contain Orka's main function"""
# import
from __future__ import with_statement
from helpers import runProcess
import sys
import os
import inject
import hardwareAnalyser
import APIAnalyser
import re
import csv
import config
import glob
import argparse
import matplotlib.pyplot as plt
from matplotlib import rcParams
import distutils.spawn
import profiles

# Const
ORKAHOME = os.environ['ORKA_HOME']
if ORKAHOME[-1] == "/":
    ORKAHOME = ORKAHOME[:-1]
ORKASDK = os.environ['ANDROID_HOME']

ADB = ORKASDK + "/platform-tools/adb"

pathConf = ORKAHOME + "/conf.ini"
pathApiCosts = ORKAHOME + '/dependencies/api_costs.csv'
pathApiFound = ORKAHOME + '/working/apifound'

# shell arguments parser
parser = argparse.ArgumentParser(description='Run energy profiling')
parser.add_argument('--skip-inj', dest='skipInjection', action='store_const',
                    const=True, default=False,
                    help='use this option to skip the injection phase')
parser.add_argument('--skip-simul', dest='skipSimul', action='store_const',
                    const=True, default=False,
                    help='use this option to skip the simulation phase')
parser.add_argument('--skip-analysis', dest='skipAn', action='store_const',
                    const=True, default=False,
                    help='use this option to skip the analysis phase')
parser.add_argument('--skip-graph', dest='skipGraph', action='store_const',
                    const=True, default=False,
                    help='use this option to skip rendering graph')
parser.add_argument('--batch', dest='batchMode', action='store_const',
                    const=True, default=False,
                    help='use this option to proccess each run independently')
parser.add_argument('--app', dest='argApp',
                    help='use this option to use parameters for app location ' \
                    'instead of config.ini')
parser.add_argument('--mr', dest='argMonkey',
                    help='use this option to use parameters for the ' \
                    'monkeyrunner script location instead of config.ini')
parser.add_argument('--method', dest='method',
                    default="Monkeyrunner",
                    help='use this option to change the testing method ' \
                    'allowed options are: DroidMate-2, monkeyrunner')
parser.add_argument('--avd', dest='avd',
                    help='use this option to set which avd to use')
parser.add_argument('--port', dest='port',
                    default="5554",
                    help='use this option to set which port the avd should run on')
parser.add_argument('--pickle', dest='pickle',
                    default="",
                    help='use this option to set the pickle location for' \
                    'ACVTool')
parser.add_argument('--category', dest='category',
                    default="1000",
                    help='use this option to set the options' \
                    'for DroidMate-2')

def getPackageInfo(app):
    """Retrieve package information from an apk."""

    #NB bwestfield, if this is ever changed back to a web app, this
    # need to check the type is unicode
    if not isinstance(app,str):
        msg = "supplied app name is of type {}, expected a string"
	raise AttributeError(msg.format(type(app)))

    if not os.path.isfile(app):
        raise OSError("cannot find specified app - "+ app)

    buildtools = glob.glob(ORKASDK + '/build-tools/*')
    if not len(buildtools):
        raise OSError('No version of build-tools found in SDK folder.')
    AAPT = buildtools[0] + '/aapt'

    # Get package name
    cmd = AAPT + " dump badging " + app
    cmd += " | grep -oP \"(?<=package: name=')\S+\""

    out = runProcess(cmd, getStdout = True)
    packName = out[:-2]
    print("packName: " + packName)

    # Build package directory

    packDir = ''
    tmp = packName.split('.')

    for x in range(0, len(tmp) - 1):
        packDir += tmp[x] + '/'

    packDir += tmp[len(tmp) - 1]

    # Get activity name
    cmd = AAPT + " dump badging " + app
    cmd += " | grep -oP \"(?<=launchable-activity: name=')\S+\" | head -n 1"

    out = runProcess(cmd, getStdout = True)
    actName = out[:-2]

    # Build componentName
    compName = packName + '/' + actName

    return packName, packDir, compName

def _getAppUid(path):
    """Retrieve application uid from Orka's temp file."""
    with open(path, 'r') as f:
        uid = f.readline().strip()
        f.close()
        uid = uid[-3:]
        if uid.startswith('0'):
            uid = uid[-2:]
        return 'u0a' + uid

def _loadAPIcosts(path):
    """Build the dict of reference API costs."""
    with open(path, 'r') as f:
        reader = csv.reader(f)
        costs = dict()
        for row in reader:
            api = row[0].split("(")[0]
            value = float(row[1])
            costs[api] = value
        f.close()
    return costs

def _instrument(app, packName, packDir):
    """Generate an injected, signed APK file from an initial APK."""
    packageFolders = packDir.split("/")
    rootPackageDir = "/".join(packageFolders[:2])
    cmd = [ORKAHOME + "/src/instrument.sh", app, packName, rootPackageDir]
    cmd = ' '.join(cmd)
    exitCode = runProcess(cmd)
    while exitCode != None and exitCode == "Exit code 2":
        firstSlashIndex = packDir.find("/")
        if firstSlashIndex == -1:
           raise RuntimeError("Could not find smali folders")
        packDir = packDir[firstSlashIndex+1:]
        exitCode = None
        cmd = [ORKAHOME + "/src/instrument.sh", app, packName, packDir]
        cmd = ' '.join(cmd)
        exitCode = runProcess(cmd)
    return os.path.exists(pathApiFound)

def _runSimulation(pathOrkaApk, packName, avd, scriptCmd,
    nRuns, port, pickle):
    """Runs a command on an injected apk."""
    cmd = [ORKAHOME + "/src/simulationMaster.sh ", pathOrkaApk, packName, avd,
        scriptCmd, nRuns, port, pickle]
    cmd = ' '.join(cmd)
    runProcess(cmd)

def _analyseResults(emul, packName, apiCosts):
    """Generate final results and graphs from raw results."""
    resultsDir = ORKAHOME + '/results_{}/{}'.format(emul, packName)
    appUid = _getAppUid(resultsDir + '/appuid')
    rcParams.update({'figure.autolayout': True})
    f, (ax1, ax2) = plt.subplots(1, 2)
    f.suptitle(packName + ' energy profile\n')
    ax1.set_title('Breakdown by routine')
    ax1.set_aspect('equal')
    ax2.set_title('Breakdown by component')
    ax2.set_aspect('equal')

    APIAnalyser.analyseAPIData(resultsDir, apiCosts, ax1)
    hardwareAnalyser.analyseHardwareData(resultsDir, appUid, ax2)

def main(args):
    """Run Orka using provided configuration."""
    # load api costs
    apiCosts = _loadAPIcosts(pathApiCosts)

    # parse the configuration file
    emul, apps, monkey, monkeyInputs, nRuns = config.parseConfig(pathConf,
        args.batchMode)
    if args.argApp:
        apps = [args.argApp]
    if args.argMonkey:
        monkeyInputs = [args.argMonkey]
    if args.avd:
        emul = args.avd

    for app, monkeyInput in zip(apps, monkeyInputs):
        #get package name and directory
        packName, packDir, compName = getPackageInfo(app)
        outputDir =  "{}/working/{}".format(ORKAHOME, packName)
        pathOrkaApk = outputDir + "/dist/orka.apk"

        # inject logging into app
        if not (args.skipInjection and os.path.exists(pathOrkaApk)):
            _instrument(app, outputDir, packDir)

        resultsDir = "{}/results_{}/{}/run1".format(ORKAHOME, emul, packName)
        logcat = resultsDir + '/logcat.txt'
        batterystats = resultsDir + '/batterystats.txt'

        # simulate user interactions
        if not (args.skipSimul and os.path.exists(logcat) \
            and os.path.exists(batterystats)):
            if args.method == "DroidMate-2":
                scriptCmd = ("java -jar vendor/orka/dependencies/DM-2.jar "+
                    "--Exploration-apksDir=" +
                    outputDir + "/dist --Output-outputDir=" + resultsDir
                    + "/droidmate ")
                scriptCmd += ' '.join(profiles.appendTestProfile(args.category))
            else:
                scriptCmd = ' '.join([ORKASDK+"/tools/bin/monkeyrunner",
                    monkey, compName, monkeyInput, args.port])
            scriptCmd = "\'" + scriptCmd + "\'"
            print ("Running simulation with command: " + scriptCmd)
            _runSimulation(pathOrkaApk, packName, emul, scriptCmd, nRuns,
                args.port, args.pickle)

        # render results
        if not args.skipAn:
            _analyseResults(emul, packName, apiCosts)
            if not args.skipGraph:
                plt.show()

if __name__ == "__main__":
    args = parser.parse_args()
    acvtoolPath = distutils.spawn.find_executable('acv');
    if acvtoolPath is None or  acvtoolPath == "":
        print ("Cannot find ACVTool installation on machine.")
        exit(1);
    main(args)
