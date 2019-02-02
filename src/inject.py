#!/usr/bin/python
"""Contain Orka's injector main function and auxiliary functions."""
from __future__ import with_statement
import  os,  glob, fnmatch
import sys
import re
import datetime

ORKAHOME = os.environ['ORKA_HOME']
outputExtension = ".orkatmp"

def _isAppFile(path):
    """Check if file is part of the app."""
    fileName = path.split('/')[-1]
    notAppFile = fnmatch.fnmatch(fileName,'*R$*.smali') \
        or fileName.endswith("R.smali") \
        or fileName.endswith("Logger.smali") \
        or fileName.endswith(outputExtension) # for testing only ?
    return not notAppFile

def _addMethodEnterLog(output):
    """Add code logging that a new method has been enterred."""
    output.write('    invoke-static {}, Lcom/test/bbutton/Logger;->methodEnterLog()V\n\n')

def _addMethodExitLog(output):
    """Add code logging that a method has been left."""
    output.write('    invoke-static {}, Lcom/test/bbutton/Logger;->methodExitLog()V\n\n')

def _addCustomLog(output, msg, registerNumber):
    """Add code logging a user defined message."""
    output.write('    const-string v' + str(registerNumber) + ', "' + msg + '"\n\n')
    output.write('    invoke-static/range {v'+str(registerNumber)+' .. v' + \
        str(registerNumber) + \
        '}, Lcom/test/bbutton/Logger;->customLog(Ljava/lang/String;)I\n\n')

def _addAllLogAPI(output, apis, registerNumber):
    """Add code logging a list of API calls."""
    for api in apis:
        msg = '    API call ' + api
        _addCustomLog(output, msg, registerNumber)

def _getPackageId(source):
    """Get the app id and the class id from the first line of the file."""
    line = source.readline()
    source.seek(0)
    if not line.startswith('.class'):
        raise RuntimeError("Couldn't parse packageId")
    start = line.find('Lcom')
    end = line.rfind('/')
    appId = line[start:end]
    classId = line[end + 1: -2]
    return appId, classId

def _getNameFromSig(line, className):
    """Get the method name from its signature."""
    methodName = className + '/' + line.split()[-1]
    methodName = methodName[:methodName.find('(')]
    return methodName

def _getNameFromInvoke(line, namespace = 'Landroid/'):
    """Get the name of the first API bellonging to a given namespace."""
    # start at + 1 because we do not want the preceeding L
    # stops at ( and replace ;-> with /
    start = line.find(namespace) + 1
    end = line.find('(')
    return line[start:end].replace(';->', '/')

def _lineHasInvoke(line, namespace, subset = None):
    """
    Check whether line contains a method invocation in a given namespace and
        subset.
    """
    line = line.strip()

    split = line.split()
    if len(split) == 0:
        return False
    fullMethodName = split[-1]
    if not line.startswith('invoke-') or not fullMethodName.startswith(namespace):
        return False
    elif not subset:
        return True
    else:
        return _getNameFromInvoke(line, namespace)[len(namespace):] in subset

def _lineHasApiInvoke(line):
    """Check whether line contains an Android API invocation."""
    return _lineHasInvoke(line, 'Landroid/')

def _hasApis(source):
    """Check whether method contains Android API invocations."""
    pos = source.tell()
    apiFound = False
    while True:
        line = source.readline().strip()
        if _lineHasApiInvoke(line):
            apiFound = True
            break
        elif line.startswith('.end'):
            break
    return apiFound

def _jumpToInjectedMethod(source, output, injectedMethods, className):
    """Read file until next method to inject."""
    while True:
        line = source.readline()
        # EOF
        if not line:
            return False

        output.write(line)

        strip = line.strip()
        # if method declaration and not constructor and has API return True
        if strip.startswith('.method') \
            and _getNameFromSig(strip, className) in injectedMethods:
            return True

def _needMoveParam(local, parameters):
    """Checks if the parameters need to be moved into the first 16 registers."""
    # if there are 16 locals, then there is no need to move
    # otherwise, adding a local will push a parameter out of 4-bit registers
    return local < 16 and (local + parameters) >= 16

def _remapParameters(line, pMap):
    """Remap parameters."""
    strPattern = '|'.join(pMap.keys())
    pattern = re.compile(strPattern)
    return pattern.sub(lambda x: pMap[x.group()], line)

def _getParametersList(fi):
    """Get the method parameters and their type."""
    # adding invisible parameter for this
    param = {0: 'L'}
    # store current position
    pos = fi.tell()

    while True:
        line = next(fi)
        lineArray = line.split()
        # if no more parameters, go back to start of file and return
        if not len(lineArray) or lineArray[0] != '.param':
            fi.seek(pos)
            return param

        # objects always start with L and others are just letters
        pIndex = int(lineArray[1][1])
        pType = lineArray[-1][0]
        param[pIndex] = pType

def _getParametersTotalSize(parameters):
    """Get the total number of parameters from the parameter dict."""
    total = 0
    for value in parameters.values():
        if value.startswith('J') or value.startswith('D'):
            total += 2
        else:
            total += 1
    return total

def _injectMethodPrologue(source, output):
    """Inject the prologue of current method."""
    remappedParam = False
    parameterMap = {}
    while True:
        line = source.readline()
        if line == '':
            return newReg, remappedParam, parameterMap
        strip = line.strip()
        if strip.startswith('.locals'):
            lineArray = line.split('.locals')
            newReg = int(lineArray[1])

            line = lineArray[0] + '.locals ' + str(newReg + 1) + '\n'
            output.write(line)

            param = _getParametersList(source)
            paramSize = _getParametersTotalSize(param)

            remappedParam = _needMoveParam(newReg, paramSize)
            # if remappedParam:
                # logfile.write("This line require remapping parameters. locals %d parameters %d\nParameters:" % (newReg, paramSize))
                # for key, value in sorted(param.iteritems()):
                    # logfile.write(str(key) + " " + str(value) + ",")
                # logfile.write("\n")

            # compute parameters map
            if remappedParam:
                for key, value in sorted(param.iteritems()):
                    # move two registers for 64bit types
                    parameterMap['p' + str(key)] = 'v' + str(newReg)
                    if value =='J' or value =='D':
                        parameterMap['p' + str(key+1)] = 'v' + str(newReg+1)
                        newReg += 2
                    else:
                        newReg += 1

        elif strip.startswith('.prologue') or 'droidmate' in strip:
            _addMethodEnterLog(output)
            # move parameters
            if remappedParam:
                for key, item in sorted(param.iteritems()):
                    reg = 'p'+str(key)
                    mapping = parameterMap[reg]
                    # only doubles and longs use two
                    # registers, so use move-wide for them
                    if item == 'J' or item =='D':
                        output.write('     move-wide/16 '\
                            + mapping + ', ' + reg + '\n\n')
                    elif item =='L':
                        output.write('     move-object/from16 '\
                            + mapping +', ' + reg +'\n\n')
                    else:
                        output.write('     move/from16 '\
                            + mapping +', ' + reg +'\n\n')
            output.write(line)
            return newReg, remappedParam, parameterMap

        else:
            output.write(line)

def _injectMethodBody(source, output, newReg, remappedParam, parameterMap,
    appId, injectedMethods):
    """Inject the body of current method."""
    depth = 0
    apiCalls = [[]]
    exitLogged = False
    lineNumber = "-1"
    # logfile = open("injectlogfile.txt", "a")
    # logfile.write("injecting into method body of " + source.name + "\n")

    while True:
        line = source.readline()
        # logfile.write(str(datetime.datetime.now()).split('.')[0] + line+"\n")

        if line == '':
            # logfile.close()
            return

        # Skip blanklines
        if not line.strip():
            output.write('\n')
            continue

        if remappedParam:
            line = _remapParameters(line, parameterMap)

        strip = line.strip()
        if strip.startswith(':goto'):
            # if a goto detected, need to start using a different list to store
            # the apis so that only those on that level are logged before goto
            # commands
            # the depth location stores a list of all apis at that depth
            depth += 1
            try:
                apiCalls[depth] = []
            except:
                apiCalls.append([])

        elif strip.startswith('goto'):
            # a loop commands has been found, log all apis for that
            if depth > 0:                   # FIXME should always be the case?
                # log apis from the list and lower the tier
                _addAllLogAPI(output, apiCalls[depth], newReg)
                depth -= 1

        elif _lineHasApiInvoke(strip):
            apiName = _getNameFromInvoke(strip)
            apiCalls[depth].append('l{} {}'.format(lineNumber, apiName))

        elif _lineHasInvoke(strip, appId, injectedMethods):
            name = _getNameFromInvoke(strip, appId)[len(appId):]
            msg = 'invoking subroutine l{} {}'.format(lineNumber, name)
            _addCustomLog(output, msg, newReg)

        elif strip.startswith('.line') or strip.startswith('return') \
            or strip.startswith('.end method'):
            _addAllLogAPI(output, apiCalls[0], newReg)
            apiCalls[0] = []

            if strip.startswith('.line'):
                lineNumber = strip.split()[-1]
            elif not exitLogged:
            # if return or end of method, log an exit method message
                _addMethodExitLog(output)
                exitLogged = True

        output.write(line)
        if strip.startswith('.end method'):
            # logfile.close()
            return

def _injectFile(path, injectedMethods):
    """Inject a single file."""
    with open(path,'r') as source:
        print ("Injecting into " + path)
        with open(path + outputExtension, 'w') as output:
            appId, className = _getPackageId(source)
            while _jumpToInjectedMethod(source, output, injectedMethods, className):
                newReg, remappedParam, parameterMap = _injectMethodPrologue(source,
                    output)
                _injectMethodBody(source, output, newReg, remappedParam,
                    parameterMap, appId, injectedMethods)
            output.close()
        source.close()
    # overwrite the original file
    os.rename(path + outputExtension, path)

def _scanFile(path, methodsToInject):
    """Scan a single file and get the set of its methods to inject."""
    with open(path,'r') as source:

        className = _getPackageId(source)[1]

        while True:
            line = source.readline()
            # EOF
            if not line:
                return

            line = line.strip()
            # if line declaration and not constructor and has API
            if line.startswith('.method'):
                methodName = _getNameFromSig(line, className)

                if _hasApis(source):
                    methodsToInject.add(methodName)

        source.close()
        return

def _scan(path, filesToInject, methodsToInject):
    """Get the set of files and method to inject from a initial set of files."""
    # if path is an application file, it needs to be scanned and injected
    if os.path.isfile(path) and _isAppFile(path):
        _scanFile(path, methodsToInject)
        filesToInject.add(path)

   # recurse if path is a directory
    elif os.path.isdir(path):
        if path.endswith('/'):
            path += '*'
        else:
            path += '/*'

        files = glob.glob(path)

        for f in files:
            _scan(f, filesToInject, methodsToInject)


def main(argv):
    """Inject a set of files."""
    filesToInject = set()
    methodsToInject = set()

    # Clear log file
    # logfile = open("injectlogfile.txt", "w")
    # logfile.close()
    for path in argv:
        # check there are files to proccess
        files = glob.glob(path)
        if not files:
            raise RuntimeError('No files mathing path: ' + path)
        print 'inject.py: injecting files at: ' + path

        _scan(path, filesToInject, methodsToInject)

    for path in filesToInject:
        _injectFile(path, injectedMethods = methodsToInject)

if __name__ == "__main__":
    main(sys.argv[1:])
