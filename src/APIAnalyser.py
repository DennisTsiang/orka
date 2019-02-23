"""Contain functions analysing the logcat data."""

from __future__ import with_statement
import re
import os
import glob

from routine import Routine
import helpers

def _sanitise(name):
    """Format string."""
    sanitised = name.replace("/",".")
    sanitised = re.sub(r'\s+', '',sanitised).strip()
    return sanitised

def _addRoutineCall(apiDicts, routine_name):
    """Add routine call to given api dict."""
    for apiData in apiDicts:
        if not apiData.has_key(routine_name):
            #if not in dictionary, add method
            apiData[routine_name] = Routine(routine_name)

        apiData[routine_name].addCall()

def _addSubroutineCall(apiDicts, routine_name, subroutine, lineNumber):
    """Add subroutine call to given routine at specified lineNumber."""
    for apiData in apiDicts:
        apiData[routine_name].subroutines[lineNumber] = subroutine


def _addAPICall(apiDicts, routineStack, lineStack, apiName):
    """Add API call."""
    if len(routineStack) != len(lineStack):
        raise RuntimeError(
            'Error in call stack: Routine stack size neq to line stack size\n' +
            'Routine stack size: %d\nLine stack size: %d' %
            (len(routineStack), len(lineStack)))
    for apiData in apiDicts:
        for routine_name, lineNumber in zip(routineStack, lineStack):
            apiData[routine_name].addApi(apiName, lineNumber)

def _addToStack(stack, tid, item):
    """Add item to stack corresponding to given tid."""
    if not stack.has_key(tid):
            #if not in dictionary, add method
            stack[tid] = []
    stack[tid].append(item)

# bwestfield - function that draws the APIs from logcat then compares to the list
# of API costs. Returns a dictionary of Routine object
def _parseData(logcat, apiDataAggregated):
    """
    Parse the logcat data.

    Keyword arguments:
    logcat -- path to the logcat file to parse
    apiDataAggregated -- dict containing the logcat data aggregated over all runs
    """

    apiData = {}
    routineStack = {}
    lineStack = {}
    routine_name = ''
    lineCount = 0

    with open(logcat, 'r') as log:
        for index, line in enumerate(log):
            lineCount += 1
            name = _sanitise(line.split(' ')[-1])
            tid = line.split()[3].strip()
            lineNumber = line.split()[-2][1:]

            #then one of the inserted logs
            if line.find(' entering ') >= 0:
                #store the current method we are in
                routine_name = name
                _addRoutineCall([apiData, apiDataAggregated], routine_name)
                _addToStack(routineStack, tid, routine_name)

                if len(routineStack[tid]) > 1 and \
                (tid not in lineStack or \
                len(routineStack[tid]) - len(lineStack[tid]) > 1):
                    _addToStack(lineStack, tid, -1)

            elif line.find(' invoking ') >= 0:

                _addSubroutineCall([apiData, apiDataAggregated], routine_name,
                    name, int(lineNumber))
                _addToStack(lineStack, tid, int(lineNumber))

            elif line.find(' API call ') >= 0:
                _addToStack(lineStack, tid, int(lineNumber))
                _addAPICall([apiData, apiDataAggregated], routineStack[tid],
                    lineStack[tid], name)
                lineStack[tid].pop()

            elif line.find(' exiting ') >= 0:
                if tid in lineStack and len(lineStack[tid]) > 0:
                    lineStack[tid].pop()
                expectedName = routineStack[tid].pop()
                if name != expectedName:
                    msg = 'Issue in the execution trace.\nFile: {}\nStack: {}\n'
                    msg += 'Exiting: {}\nExpected: {}\nLine: {}'
                    msg = msg.format(logcat, str(routineStack), name,
                        expectedName, lineCount)
                    raise RuntimeError(msg)
                if len(routineStack[tid]) > 0:
                    routine_name = routineStack[tid][-1]

    log.close()
    return apiData

def _processData(apiData, apiCosts, outPutDir, ax = None):
    """
    Process parsed API data.

    Keyword arguments:
    apiData -- dict containing the parsed API data
    apiCosts -- dict of reference API costs
    outputDir -- path to output directory
    ax -- Axes used to plot the pie (default None)

    Build the costs, output results to disk, print pie chart, and generate
        source-line level feedback.
    """
    routineCosts = []
    # build API Costs and get routine cost
    for routine in apiData.values():
        routine.buildApiCosts(apiCosts)
        routineCosts.append((routine.name, routine._getTotalCost()))

    # sort routine costs
    routineCosts.sort(key=lambda x: x[1], reverse=True)

    # write costs to disk
    routineCostsPath = outPutDir + '/routineCosts.csv'
    with open(routineCostsPath, 'w') as output:
        for cost in routineCosts:
            output.write(cost[0] + ',' + str(cost[1]) + '\n')
        output.close()

    # plio pie
    names, costs = (list(t) for t in zip(*routineCosts))
    if ax:
        helpers.plotPie(ax, costs, names)

    # serialize and write raw data to disk
    apiDataPath = outPutDir + '/apidata.txt'
    with open(apiDataPath, 'w') as output:
        for value in apiData.values():
            output.write(str(value.toJson()) + '\n')
        output.close()

    # generate source-line feedback
    lineFeedback = outPutDir + '/sourcelineFeedback.txt'
    toProcess = names[:10]
    with open(lineFeedback, 'w') as output:
        for name in toProcess:
            output.write(apiData[name].generateLineFeedback())
        output.close()

def analyseAPIData(resultsDir, apiCosts, ax):
    """
    Parse and process the logcat API data.

    Keyword arguments:
    resultsDir -- directory to process
    apiCosts -- dict of reference API costs
    ax -- Axes used to plot the pie (default None)
    """
    apiDataAggregated = {}
    nRuns = 0

    dirs = glob.glob(resultsDir + '/*')
    for runDir in dirs:
        logcat = runDir + '/logcat.txt'
        if not os.path.isfile(logcat):
            continue

        # get API data from logcat
        apiData = _parseData(logcat, apiDataAggregated)
        _processData(apiData, apiCosts, runDir)
        nRuns += 1

    # normalize data
    for routine in apiDataAggregated.values():
        routine.normalize(nRuns)

    # generate output
    _processData(apiDataAggregated, apiCosts, resultsDir, ax)


