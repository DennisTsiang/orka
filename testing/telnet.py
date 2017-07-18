#! /usr/bin/env monkeyrunner
# ajc515

# monkey script running a telnet script
# telnet script usage must be telnetScript port authToken <otherScriptParameters>

# usage: telnet.py componentName telnetScript <otherScriptParameters>
# use with orka: provide the telnetScript <otherScriptParameters> as script
#   input in conf.ini

from __future__ import with_statement
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice
import os
import sys

# constants
timeout = 10000
PORT = 5554

# import helpers
ORKAHOME = os.environ['ORKAHOME']
sourcepath = ORKAHOME + '/src'
sys.path.append(os.path.abspath(sourcepath))
from helpers import runProcess

# wait for device
device = MonkeyRunner.waitForConnection(timeout)

# start the activity
componentName = sys.argv[1]
device.startActivity(component=componentName)

# run the SMS TELNET script
telnetScript = sys.argv[2]
auth_token = ''
with open(os.path.expanduser('~/.emulator_console_auth_token')) as f:
    auth_token = f.readline()
    f.close()

args = [telnetScript, str(PORT), auth_token]
args.extend(sys.argv[3:])
runProcess(' '.join(args))

MonkeyRunner.sleep(5)
