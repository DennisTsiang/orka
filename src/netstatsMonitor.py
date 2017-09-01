#!/usr/bin/env python

from __future__ import with_statement
import subprocess
import os
import time
import argparse
from helpers import *

parser = argparse.ArgumentParser(description='Traffic monitoring and analysis')
parser.add_argument('-i', '--uid', nargs = 1,
                    help = 'app uid of the application to monitor')
parser.add_argument('-o', nargs = 1,
                    help = 'output path in monitoring mode')

ORKASDK = os.environ['ANDROID_HOME']
ADB = ORKASDK + "/platform-tools/adb"

def _getStatsIndexes():
    s = subprocess.check_output(ADB + ' shell cat proc/net/xt_qtaguid/stats',
            shell=True)

    lines = s.split('\n')
    i = 0
    while i < len(lines) and not lines[i].startswith('idx'):
        i += 1

    words = lines[i].split()
    uid_idx = words.index('uid_tag_int')
    rx_idx = words.index('rx_bytes')
    tx_idx = words.index('tx_bytes')

    return uid_idx, rx_idx, tx_idx

def _fetchNetworkStats(uid, uid_idx, rx_idx, tx_idx):
    cmd = '{} shell "echo \$EPOCHREALTIME; cat proc/net/xt_qtaguid/stats" | awk "NR==1 || /{}/"'.format(ADB, uid)
    s = subprocess.check_output(cmd, shell=True)

    rx_bytes = 0
    tx_bytes = 0
    fetch_time = -1

    lines = s.split('\r\n')

    for line in lines:
        if not line:
            continue
        elif fetch_time < 0:
            fetch_time = float(line)
        else:
            words = line.split()
            if words[uid_idx] == uid:
                rx_bytes += int(words[rx_idx])
                tx_bytes += int(words[tx_idx])

    return rx_bytes, tx_bytes, fetch_time

def main(outputPath, uid = '10037', tail_time = .220): # scan chrome by default

    # parse structure of netstats file
    uid_idx, rx_idx, tx_idx = _getStatsIndexes()
    with open(outputPath, 'w') as f:
        # initial values
        rx0, tx0, t0 = _fetchNetworkStats(uid, uid_idx, rx_idx, tx_idx)
        state = HwState.IDLE
        tail_start = 0

        while True:
            # fetch new values
            rx1, tx1, t1 = _fetchNetworkStats(uid, uid_idx, rx_idx, tx_idx)
            # Utilisation leads to ACTIVE state from any state
            if (rx0 != rx1 or tx0 != tx1):
                state = HwState.ACTIVE
            # End of utilisation from active leads to TAIL then IDLE
            elif (state == HwState.ACTIVE):
                state = HwState.TAIL
                tail_start = t0

            if (state == HwState.TAIL and t1 - tail_start >= tail_time):
                output = "{:10.6f} {}\n".format(t0, state)
                f.write(output)
                #print "\033c" + output
                t0 = tail_start + tail_time
                state = HwState.IDLE

            # write results
            output = "{:10.6f} {}\n".format(t0, state)
            f.write(output)
            #print "\033c" + output

            # update values
            t0 = t1
            rx0 = rx1
            tx0 = tx1


if __name__ == "__main__":

    args = parser.parse_args()
    main(args.o[0], args.uid[0])
