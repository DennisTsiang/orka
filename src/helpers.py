"""Contain helper functions used by Orka."""

import subprocess
import matplotlib.pyplot as plt
import numpy as np

def runProcess(cmd, getStdout = False):
    """Run given shell command in a new subprocess.

    Keyword arguments:
    cmd -- shell command to run
    getStdout -- if True, the function returns the stdout pipe of the subprocess
        (default False)
    """
    print "Running process " + cmd

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
