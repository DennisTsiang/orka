#!/usr/bin/python
# Copyright 2010, The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# NOTICE: the original file as been modified to start the activity prior to the
#   monkey recorded script execution

"""
Playback a monkey recorded script.

usage: monkey_player.py componentName scriptName
use with orka: provide the scriptName as ScriptInput in conf.ini
"""
from __future__ import with_statement
from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice
import sys

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
