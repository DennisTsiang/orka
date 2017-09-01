"""Contain functions to parse Orka's configuration file."""

import ConfigParser
import sys

def _checkExists(obj, name):
    """
    Check that an object exists.

    Keyword arguments:
    obj -- object to test
    name -- name of the object (for debugging)

    Raise:
    RuntimeError exception.
    """
    if len(obj) == 0:
        raise RuntimeError("No {} provided.".format(name))

def _openConfig(configFile):
    """
    Open the configuration file.

    Keyword arguments:
    configFile -- path to the configuration file

    Return:
    ConfigParser instance reading the configuration file
    """

    Config = ConfigParser.ConfigParser()

    # try to open the file, quit if fail
    try:
        with open(configFile) as f:
                Config.readfp(f)
        f.close()
    except IOError:
        print "Error reading " + configFile
        sys.exit(1)

    return Config

def parseConfig(configFile, batchMode = False):
    """
    Get the configuration parameters by parsing the config file.

    Keyword arguments:
    configFile -- path to the configuration file
    batchMode -- set to true if Orka is executed in batchMode (default false)
    """

    Config = _openConfig(configFile)

    # get app, emulators and testing option
    emul = Config.get("Emulators", "names")

    if not batchMode:
        app = Config.get("Application", "path")
        monkey = Config.get("Monkeyrunner script", "path")
        monkeyInput = Config.get("Monkeyrunner script", "input")
        nRuns = Config.get("Monkeyrunner script", "runs")

        _checkExists(app, "application")
        _checkExists(emul, "emulators")
        _checkExists(monkey, "test script")

        if len(monkeyInput) == 0:
            print "WARNING: No script input provided."

        if len(nRuns) == 0:
            nRuns = "1"

        return emul, [app], monkey, [monkeyInput], nRuns

    else:
        mainDir = Config.get("Batch run", "Main Directory")
        if not mainDir.endswith('/'):
            mainDir += '/'

        appNames = Config.get("Batch run", "Application Names").split(' ')
        monkey = Config.get("Batch run", "Monkey Intrepetter")
        nRuns = Config.get("Batch run", "Runs")

        apps = []
        monkeyInputs = []

        for name in appNames:
            filePrefix = mainDir + name + '/' + name
            apps.append(filePrefix + '_debug.apk')
            monkeyInputs.append(filePrefix + '.txt')

        return emul, apps, monkey, monkeyInputs, nRuns

