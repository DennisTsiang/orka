"""Contain helper functions used by Orka."""

import subprocess
import matplotlib.pyplot as plt
import numpy as np
import time
import re

from routine import Routine
from const import *

def _logcatDateTimeToEpoch(date, tim):

    # split date and miliseconds
    tim, ms = tim.split('.')

    # build date-time
    year = str(time.gmtime().tm_year)
    date_time = '{}-{} {}'.format(year, date, tim)

    # parse pattern
    pattern = '%Y-%m-%d %H:%M:%S'
    t = time.strptime(date_time, pattern)
    epoch = time.mktime(t) + float(ms) * 0.001
    return epoch

def sanitise(name):
    """Format string."""
    sanitised = name.replace("/",".")
    sanitised = re.sub(r'\s+', '',sanitised).strip()
    return sanitised

def parseLogcatEntry(logcat):
    line = logcat.readline().strip()
    if not line:
        return None
    elif line.startswith('-'):
        return parseLogcatEntry(logcat)

    split = line.split()
    entry = {}
    entry['time'] = _logcatDateTimeToEpoch(date = split[0], tim = split[1])
    entry['tid'] = split[3]
    entry['methodName'] = sanitise(split[-1])

    if line.find(' entering ') >= 0:
        entry['type'] = LogcatEntryType.ENTER
    elif line.find(' invoking ') >= 0:
        entry['type'] = LogcatEntryType.INVOKE
    elif line.find(' API call ') >= 0:
        entry['type'] = LogcatEntryType.API_CALL
    elif line.find(' exiting ') >= 0:
        entry['type'] = LogcatEntryType.EXIT
    return entry

def addToStack(stack, tid, item):
    """Add item to stack corresponding to given tid."""
    if not stack.has_key(tid):
            #if not in dictionary, add method
            stack[tid] = []
    stack[tid].append(item)

def popFromStack(stack, tid, expItem, fileName = "unknown",
    lineCount = "unknown"):

    poppedItem = stack[tid].pop()
    if poppedItem != expItem:
        stack[tid].append(poppedItem)
        msg = 'Issue in the execution trace.\nFile: {}\nStack exiting: {}\n'
        msg += 'Logcat exiting: {}\nLine: {}\nStack: {}\n'
        msg = msg.format(fileName, poppedItem,  expItem, lineCount, str(stack))
        raise RuntimeError(msg)

def addRoutineCall(routineDicts, routine_name):
    """Add routine call to given api dict."""
    for routineDict in routineDicts:
        if not routineDict.has_key(routine_name):
            #if not in dictionary, add method
            routineDict[routine_name] = Routine(routine_name)

        routineDict[routine_name].addCall()

def runProcess(cmd, getStdout = False):
    """Run given shell command in a new subprocess.

    Keyword arguments:
    cmd -- shell command to run
    getStdout -- if True, the function returns the stdout pipe of the subprocess
        (default False)
    """
    print ("Running process " + cmd)

    if not (isinstance(cmd, unicode) or isinstance(cmd, str)):
        raise AttributeError('invalid command supplied as parameter')

    # run command
    if getStdout:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    else:
        p = subprocess.Popen(cmd, shell=True)
    p.wait()

    # check return code
    if p.returncode != 0:
        error = "invalid command attempted to be executed in runProcess - {}"
        raise RuntimeError(error.format(cmd))

    # if needed, return stdout pipe
    if getStdout:
        return str(p.communicate()[0])

def plotPie(ax, values, labels, minimumThreshold = 1):
    """
    Plot a pie chart.

    Keyword arguments:
    ax -- Axes used to plot the pie (default None)
    values -- list of values displayed on the chart, sorted in decreasing order
    labels -- list of labels displayed on the chart (the ith label corresponds
        to the ith value)
    minimumThreshold -- the minimum size of s slice of the pie(default 1)
    """

    # normalize values
    values = np.multiply(values, 100.0 / sum(values)).tolist()

    # find smallest index with value greater than minimumThreshold
    thresholdIndex = 0
    while thresholdIndex < len(values) \
        and values[thresholdIndex] > minimumThreshold:
        thresholdIndex += 1

    # aggregate values lower than minimumThreshold
    remaining = sum(values[thresholdIndex:])
    # remove these values from the chart
    values = values[:thresholdIndex]
    labels = labels[:thresholdIndex]
    # add the aggregated value
    if remaining > 0.1:
        values.append(remaining)
        labels.append('Others')

    # plot pie
    ax.pie(values, radius = 0.7, labels=labels, autopct='%1.1f%%')
    plt.gcf().subplots_adjust(bottom=0.25) #?
