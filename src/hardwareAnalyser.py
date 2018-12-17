"""Contain functions analysing the batterystats data."""

from __future__ import with_statement
import re
import os
import helpers
import glob

def _addCost(costDict, component, cost):
    """
    Add cost of component in the cost dict.

    Keyword arguments:
    costDict -- cost dictionnary
    component -- name of the component
    cost -- cost to be added
    """
    if component in costDict:
        costDict[component] += cost
    else:
        costDict[component] = cost

# bwestfield - function that draws the APIs from logcat then compares to the list
# of API costs. Returns a dictionary of Routine object
def _parseData(batterystats, hardwareDataAggregated, appUid):
    """
    Parse the batterystats data.

    Keyword arguments:
    batterystats -- path to the batterystats file to parse
    hardwareDataAggregated -- dict containing the hardware data aggregated
        over all runs
    appUid -- uid of tested application
    """
    print ("batterystats file: %s, hardwareDataAggregated: %s, appUid: %s" % (batterystats, hardwareDataAggregated, appUid))
    hardwareData = {}
    with open(batterystats,'r') as source:
        # consume file until section "Estimated power use"
        while True:
            line = source.readline()
            # EOF
            if not line:
                raise RuntimeError('No hardware usage data found')
            elif line.strip().startswith('Estimated power use'):
                break
        # consume capacity line
        source.readline()

        # Parse hardware energy usage
        while True:
            line = source.readline().strip()
            # End of section
            if not line:
                return hardwareData
            # ignore line related to other applications
            elif line.startswith('Uid ') \
                and line.find(appUid) == -1:
                continue
            # add cost
            else:
                words = line.split(':')
                cost = 0
                if line.startswith('Uid '):
                    words[0] = 'CPU'
                    floatRegex = r"cpu=(\d+\.\d+)"
                    matches = re.search(floatRegex, line)
                    cost = float(matches.group(1))
                else:
                    values = words[1].split(' ')
                    cost = float(values[1].replace(',', '.'))
                _addCost(hardwareData, words[0], cost)
                _addCost(hardwareDataAggregated, words[0], cost)

def _processData(hardwareData, outputDir, ax = None):
    """
    Output parsed hardware data to disk and plot pie chart.

    Keyword arguments:
    hardwareData -- dict containing the parsed hardware data
    outputDir -- path to output directory
    ax -- Axes used to plot the pie (default None)
    """
    hardwareData = hardwareData.items()
    hardwareData.sort(key=lambda x: x[1], reverse=True)

    hwCostsPath = outputDir + '/hardwareCosts.csv'
    with open(hwCostsPath, 'w') as output:
        for cost in hardwareData:
            output.write(cost[0] + ',' + str(cost[1]) + '\n')
        output.close()

    names, costs = (list(t) for t in zip(*hardwareData))

    if ax:
        helpers.plotPie(ax, costs, names, 0.1)

def analyseHardwareData(resultsDir, appUid, ax):
    """
    Analyse the batterystats data.

    Keyword arguments:
    resultsDir -- directory to process
    appUid -- uid of tested application
    ax -- Axes used to plot the pie (default None)
    """
    hardwareDataAggregated = {}
    nRuns = 0

    dirs = glob.glob(resultsDir + '/*')
    for runDir in dirs:
        batterystats = runDir + '/batterystats.txt'
        if not os.path.isfile(batterystats):
            continue

        # get API data from batterystats
        hardwareData = _parseData(batterystats, hardwareDataAggregated, appUid)
        _processData(hardwareData, runDir)
        nRuns += 1

    # normalize data
    for component in hardwareData.keys():
        hardwareData[component] /= nRuns

    # generate output
    _processData(hardwareDataAggregated, resultsDir, ax)
