#!/usr/bin/python
# ajc515

# usage: monkey_player.py componentName scriptName
# use with orka: provide the scriptName as ScriptInput in conf.ini

from __future__ import with_statement
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice
import sys
import time

# Lookup table to map command strings to functions that implement that
# command.
CMD_MAP = {
    'TOUCH': lambda dev, arg: dev.touch(**arg),
    'DRAG': lambda dev, arg: dev.drag(**arg),
    'PRESS': lambda dev, arg: dev.press(**arg),
    'TYPE': lambda dev, arg: dev.type(**arg),
    'WAIT': lambda dev, arg: MonkeyRunner.sleep(**arg)
    }

timeout = 10000
componentName = sys.argv[1]
scriptName = sys.argv[2]

device = MonkeyRunner.waitForConnection(timeout)
device.startActivity(component=componentName)

time.sleep(3)

with open(scriptName, 'r') as script:
    # process script
    for line in script:
        (cmd, rest) = line.split('|')
        try:
            # Parse the pydict
            rest = eval(rest)
        except:
            print 'unable to parse options'
            continue

        if cmd not in CMD_MAP:
            print 'unknown command: ' + cmd
            continue

        CMD_MAP[cmd](device, rest)
    script.close()
