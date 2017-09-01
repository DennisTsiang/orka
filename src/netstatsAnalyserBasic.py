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

def _parseNetstatsEntry(netstats, firstPass = False):
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
        if firstPass and state != HwState.ACTIVE:
            return _parseNetstatsEntry(netstats, firstPass = True)
        entry['state'] = state
        return entry
    else:
        return None

def _updateStateFromNetstatsEntry(entry, state, costs, _):
    state['wifi_state'] = entry['state']
    return

def _updateCost(costs, state, currentTime):
    #
    if costs['_lastUpdate'] != -1:
        delta_time = currentTime - costs['_lastUpdate']
        costs[state['wifi_state']] += delta_time

    # update last update time
    costs['_lastUpdate'] = currentTime



def _processEntry(entry, updateState, parser, file, costs, state):
    t = entry['time']
    # compute cost for last interval
    _updateCost(costs, state, t)
    updateState(entry, state, costs, file)
    newEntry = parser(file)
    return newEntry

def _parseData(netstatsPath, outputPath):

    with open(netstatsPath) as netstats:
        # read first line of each file
        net_entry = _parseNetstatsEntry(netstats, firstPass=True)

        costs = {'_lastUpdate': -1, 'ACTIVE': 0, 'IDLE': 0, 'TAIL': 0}
        state = {'wifi_state': 'IDLE'}

        while True:

            if not net_entry:
                break

            net_entry = _processEntry(net_entry,
                _updateStateFromNetstatsEntry,
                _parseNetstatsEntry,
                netstats,
                costs,
                state)

        netstats.close()

        return costs

def _processData(costs, runDir):
    outputPath = runDir + '/tailEnergyFeedbackBasic.txt'
    with open(outputPath, 'w') as out:
        for routine in costs:
            if routine is not '_lastUpdate':
                out.write("{} {}\n".format(routine, costs[routine]))


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
        netstats = runDir + '/netstats.txt'
        if not os.path.isdir(runDir) or not os.path.isfile(netstats):
            continue

        costs = _parseData(netstats, runDir)
        _processData(costs, runDir)

if __name__ == "__main__":
    analyseNetstatsData(sys.argv[-1])
