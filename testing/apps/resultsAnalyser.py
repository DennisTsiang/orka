from __future__ import with_statement
import os
import math

ORKA = 'orka'
PETRA = 'petra'
ERR = 'error'

ORKA_HOME = os.environ['ORKA_HOME']
TEST_DIR = ORKA_HOME + '/testing/app/'
PETRA_RES = '/petra_results/routineCosts.csv'
ORKA_RES = '/orka_results/routineCosts.csv'

class resultsComparator:

    def __init__(self):
        self.res = {}

    def addEntry(self, appName, sig, tool, usage):
        if not self.res.has_key(appName):
            self.res[appName] = {}

        if not self.res[appName].has_key(sig):
            self.res[appName][sig] = {}

        self.res[appName][sig][tool] = usage

    def getEntry(self, appName, sig, tool):
        if not self.res.has_key(appName) \
        or not self.res[appName].has_key(sig) \
        or not self.res[appName][sig].has_key(tool):
            return None
        else:
            return self.res[appName][sig][tool]

    def getStringEntry(self, appName, sig, tool):
        res = self.getEntry(appName, sig, tool)
        if res is None:
            return ''
        else:
            return str(res)

    def toCSV(self, path):
        with open(path, 'w') as f:
            f.write('application_name,signature,orka_estimate,petra_estimate,error\n')
            for appName in self.res.keys():
                for sig in self.res[appName].keys():
                    orkaEst = self.getStringEntry(appName, sig, ORKA)
                    petraEst = self.getStringEntry(appName, sig, PETRA)
                    error = self.getStringEntry(appName, sig, ERR)
                    f.write(','.join([appName, sig, orkaEst, petraEst, error]))
                    f.write('\n')
            f.close()

def parseRes(resComp, appName, tool):
    if tool == ORKA:
        rawResults = appName + ORKA_RES
    elif tool == PETRA:
        rawResults = appName + PETRA_RES

    with open(rawResults) as f:
        if tool == PETRA:
            f.readline()
        for line in f:
            sig, usage = line[:-2].split(',')
            if tool == PETRA:
                sig = sig[:sig.find('(') - 1]
            usage = float(usage)
            if usage > 0:
                resComp.addEntry(appName, sig, tool, usage)
        f.close()

def processResults(resComp):
    for appName in resComp.res.keys():
        totErr = .0
        nErr = 0
        noOrka = 0
        noPetra = 0

        for sig in resComp.res[appName].keys():
            orkaEst = resComp.getEntry(appName, sig, ORKA)
            petraEst = resComp.getEntry(appName, sig, PETRA)
            if orkaEst is None:
                noOrka += 1
            elif petraEst is None:
                noPetra += 1
            else:
                err = (orkaEst - petraEst) / petraEst # math.fabs
                resComp.addEntry(appName, sig, ERR, err)
                totErr += err
                nErr += 1
        if (nErr):
            resComp.addEntry(appName,'AVGERR', ERR, totErr / nErr)
        resComp.addEntry(appName,'NOORKA', ORKA, noOrka)
        resComp.addEntry(appName,'NOPETRA', PETRA, noPetra)
        resComp.addEntry(appName, 'BOTH', ERR, nErr)

def main():
    appNames = (x for x in os.listdir(TEST_DIR) \
        if os.path.isdir(x) and os.path.isfile(x + ORKA_RES) and \
        os.path.isfile(x + PETRA_RES))

    resComp = resultsComparator()

    for appName in appNames:
        parseRes(resComp, appName, ORKA)
        parseRes(resComp, appName, PETRA)

    processResults(resComp)
    resComp.toCSV('avgerr.csv')
    return resComp

if __name__=='__main__':
    res = main()