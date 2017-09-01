from __future__ import with_statement
import sys
import os
import ast

def getScriptTime(scriptName):
    with open(scriptName) as f:
        time = 0
        while True:
            line = f.readline()
            if not line:
                f.close()
                return time + 3
            elif line.startswith('WAIT'):
                s = line.split('|')[1]
                wait = ast.literal_eval(s)
                time += wait['seconds']
            else:
                time += 0.1


def generateConfigFile(appName, powerProfilePath):
    dir = os.path.abspath(appName) + '/'
    scriptPath = "{}{}.txt".format(dir, appName)
    scriptTime = str(int(getScriptTime(scriptPath)))

    with open(dir + 'config.properties', 'w') as f:
        f.write("powerProfileFile={}\n".format(powerProfilePath))
        f.write("runs=1\n")
        f.write("trials=3\n")
        f.write("interactions=100\n")
        f.write("timeBetweenInteractions=100\n")
        f.write("apkLocation={}{}_debug.apk\n".format(dir, appName))
        f.write("outputLocation={}petra_results/\n".format(dir))
        f.write("scriptLocationPath={}\n".format(scriptPath))
        f.write("scriptTime={}\n".format(scriptTime))
        f.close()

if __name__ == "__main__":
    generateConfigFile(sys.argv[1], sys.argv[2])
