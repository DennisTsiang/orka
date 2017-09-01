#!/usr/bin/env python

from __future__ import with_statement
import argparse
import os
import sys
import glob
from helpers import *

parser = argparse.ArgumentParser(description='Traffic analysis')

ORKASDK = os.environ['ANDROID_HOME']
ADB = ORKASDK + "/platform-tools/adb"

def _parseNetstatsEntry(netstats):
    line = netstats.readline().strip()
    if not line:
        return None

    line = line.split()
    if len(line) < 2:
        return None

    entry = {}
    entry['time'] = float(line[0])
    state = line[1]

    if not state.startswith('_') and state in HwState.__dict__.keys():
        entry['state'] = state
        return entry
    else:
        return None


def _compareTimestamps(entry1, entry2):
    if not entry1 and not entry2:
        raise RuntimeError()
    elif not entry1:
        return 1
    elif not entry2:
        return -1
    else:
        return entry1['time'] - entry2['time']

def _updateStateFromNetstatsEntry(entry, state, costs, _):
    state['wifi_state'] = entry['state']

    return

def _updateStateFromLogcatEntry(entry, state, costs, file):
    # update state
    if entry['type'] == LogcatEntryType.ENTER:
        addRoutineCall([costs], entry['methodName'])
        addToStack(state['callStack'], entry['tid'], entry['methodName'])
    elif entry['type'] == LogcatEntryType.EXIT:
        popFromStack(state['callStack'], entry['tid'], entry['methodName'],
            file, state['logcat_line'])
    return

def _updateCost(costs, state, currentTime):
    #
    if costs['_lastUpdate'] != -1:
        delta_time = currentTime - costs['_lastUpdate']
        for tid in state['callStack']:
            for routine in state['callStack'][tid]:
                costs[routine].incrementTime(state['wifi_state'], delta_time)

    # update last update time
    costs['_lastUpdate'] = currentTime



def _processEntry(entry, updateState, parser, file, costs, state):
    t = entry['time']
    # compute cost for last interval
    _updateCost(costs, state, t)
    updateState(entry, state, costs, file)
    newEntry = parser(file)
    return newEntry

def _parseData(netstatsPath, logcatPath, outputPath):

    with open(netstatsPath) as netstats, open(logcatPath, 'r') as logcat:
        # read first line of each file
        net_entry = _parseNetstatsEntry(netstats)
        log_entry = parseLogcatEntry(logcat)

        costs = {'_lastUpdate': -1}
        state = {'wifi_state': 'IDLE', 'callStack': {}, 'logcat_line': 3}

        while True:

            if not net_entry and not log_entry:
                break

            if _compareTimestamps(net_entry, log_entry) < 0:
                net_entry = _processEntry(net_entry,
                    _updateStateFromNetstatsEntry,
                    _parseNetstatsEntry,
                    netstats,
                    costs,
                    state)
            else:
                log_entry = _processEntry(log_entry,
                    _updateStateFromLogcatEntry,
                    parseLogcatEntry,
                    logcat,
                    costs,
                    state)
                state['logcat_line'] += 1

        netstats.close()
        logcat.close()

        return costs

def _processData(costs, runDir):
    outputPath = runDir + '/tailEnergyFeedback.txt'
    with open(outputPath, 'w') as out:
        for routine in costs:
            if routine is not '_lastUpdate':
                out.write("{} {}\n".format(routine,
                    costs[routine].getWifiStateRatio()))


def analyseNetstatsData(resultsDir):
    """
    Parse and process the logcat API data.

    Keyword arguments:
    resultsDir -- directory to process
    apiCosts -- dict of reference API costs
    ax -- Axes used to plot the pie (default None)
    """

    dirs = (x for x in os.listdir(resultsDir) if os.path.isdir(x))
    for runDir in os.listdir(resultsDir):
        runDir = resultsDir + runDir
        logcat = runDir + '/logcat.txt'
        netstats = runDir + '/netstats.txt'
        if not os.path.isdir(runDir) or not os.path.isfile(logcat) \
            or not os.path.isfile(netstats):
            continue

        costs = _parseData(netstats, logcat, runDir)
        _processData(costs, runDir)

if __name__ == "__main__":
    analyseNetstatsData(sys.argv[-1])

    if(False):
        _parseData('invest/netstats.txt', 'invest/logcat.txt')

        for routine in costs:
            if routine is not '_lastUpdate':
                print "{} {}".format(routine, costs[routine].getWifiStateRatio())



