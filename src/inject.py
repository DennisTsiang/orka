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
    """Get the name of the first API belonging to a given namespace."""
    # start at + 1 because we do not want the preceeding L
    # stops at ( and replace ;-> with /
    start = line.find(namespace) + 1
    end = line.find('(')
    return line[start:end].replace(';->', '/')

def _getParametersFromMethod(line, pIndex, param):
    types = ['Z','B','S','C','I','J','F','D','L']
    arrayChar = '['
    regex = r"\((.*)\)"
    matches = re.findall(regex,line)
    parameters = ""
    if matches is not None and len(matches) > 0:
        parameters = matches[0]
    strIndex = 0
    arrayStack = ""
    while strIndex < len(parameters):
        if parameters[strIndex] == arrayChar:
            arrayStack += arrayChar
        elif parameters[strIndex] in types:
            if len(arrayStack) > 0:
                arrayStack += parameters[strIndex]
                param[pIndex] = arrayStack
                arrayStack = ""
            elif parameters[strIndex] == 'J' or parameters[strIndex] == 'D':
                # Longs and doubles take up two parameters
                param[pIndex] = parameters[strIndex]
                pIndex += 1
                # Later in injectMethodPrologue, both parameters will be remapped correctly
            else:
                param[pIndex] = parameters[strIndex]
            if parameters[strIndex] == 'L':
                while parameters[strIndex] != ';':
                    strIndex += 1
            pIndex += 1
        strIndex += 1
    return param

def _getParametersFromMethodInvocation(line):
    param = {}
    pIndex = 0
    if 'invoke-virtual' in line:
        # Add implicit object parameter
        param = {0: 'L'}
        pIndex = 1
    return _getParametersFromMethod(line, pIndex, param)


def _doesMethodCallMatchAPIMethodCall(line, methodName, methodsToParameters):
    """ Check if the signature of the method being invoked in line
        contains parameters that matches methods we found to have API calls
        previously. methodsToParameters stores the methods and their parameters
        that we know have API calls
    """
    if methodName not in methodsToParameters:
        return False
    invokedParams =_getParametersFromMethodInvocation(line)
    for params in methodsToParameters[methodName]:
        if params == invokedParams:
            return True

def _lineHasInvoke(line, namespace, subset = None, methodsToParameters = None):
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
        # Need to check the method we're invoking is not an abstract method
        # Abstract methods will not have any API calls
        # Needed due to function overloading in Java
        methodName = _getNameFromInvoke(line, namespace)[len(namespace):]
        return methodName in subset \
            and _doesMethodCallMatchAPIMethodCall(line, methodName, methodsToParameters)

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
        prevLine = source.tell()
        line = source.readline()
        # EOF
        if not line:
            return False

        output.write(line)

        strip = line.strip()
        # if method declaration and not constructor and has API return True
        # and not an abstract method
        if strip.startswith('.method') and 'abstract' not in strip \
        and _getNameFromSig(strip, className) in injectedMethods:
            source.seek(prevLine)
            return True

def _needMoveParam(local, parameters):
    """Checks if the parameters need to be moved into the first 16 registers."""
    # if there are 16 locals, then there is no need to move
    # otherwise, adding a local will push a parameter out of 4-bit registers
    return local < 16 and (local + parameters) >= 16

def _outOfRegisterRange(registers, limit):
    for reg in registers:
        if int(reg) > limit:
            return True
    return False

def _remapParameters(line, pMap):
    """Remap parameters."""
    strPattern = '(?=[\s,}]|$)|'.join(pMap.keys())
    pattern = re.compile(strPattern)
    remappedLine = pattern.sub(lambda x: pMap[x.group()], line)
    # Check if the new remapping included a register higher than v15
    # and if the line was a move-object line
    registerPattern = r'v(\d{2})'
    matches = re.findall(registerPattern, remappedLine)
    outOfRegisterRange = _outOfRegisterRange(matches, 15)
    if 'move-object' in remappedLine \
    and 'move-object/16' not in remappedLine \
    and 'move-object/from16' not in remappedLine \
    and outOfRegisterRange:
        remappedLine = remappedLine.replace('move-object','move-object/from16',1)
    elif re.search(r"move ", remappedLine) > 0 is not None \
    and outOfRegisterRange:
        remappedLine = remappedLine.replace('move','move/from16',1)
    return remappedLine

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

def _getParametersFromMethodSignature(line):
    param = {}
    pIndex = 0
    if 'static' not in line:
        # Add implicit object parameter
        param = {0: 'L'}
        pIndex = 1
    return _getParametersFromMethod(line, pIndex, param)

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
    # if 'subreddit/header/c.smali' in source.name:
        # logfile = open("injectlogfile.txt", "a")
        # logfile.write("injecting into method prologue of " + source.name + "\n")
    paramToTypes = {}
    paramSize = 0
    newReg = 0
    while True:
        line = source.readline()
        # if 'subreddit/header/c.smali' in source.name:
            # logfile.write(line)
        if line == '':
            return newReg, remappedParam, parameterMap, paramToTypes
        strip = line.strip()
        if strip.startswith('.method'):
            paramToTypes = _getParametersFromMethodSignature(line)
            paramSize = _getParametersTotalSize(paramToTypes)
        elif strip.startswith('.locals'):
            lineArray = line.split('.locals')
            newReg = int(lineArray[1])

            remappedParam = _needMoveParam(newReg, paramSize)
            # if remappedParam and 'subreddit/header/c.smali' in source.name:
                # logfile.write("This line require remapping parameters. locals %d parameters %d\n" % (newReg, paramSize))
                # logfile.write("\n")

            line = lineArray[0] + '.locals ' + str(newReg + 1) + '\n'
            output.write(line)

            # compute parameters map
            if remappedParam:
                for key, value in sorted(paramToTypes.iteritems()):
                    # move two registers for 64bit types
                    parameterMap['p' + str(key)] = 'v' + str(newReg)
                    if value =='J' or value =='D':
                        parameterMap['p' + str(key+1)] = 'v' + str(newReg+1)
                        newReg += 2
                    else:
                        newReg += 1
        elif strip.startswith('.param'):
            while not strip.startswith('.end param') and strip != "":
                output.write(line)
                line = source.readline()
                strip = line.strip()
            output.write(line)
        elif strip.startswith('.prologue') or 'droidmate' in strip or \
            (not '.param' in strip and not 'invoke-static' in strip):
            _addMethodEnterLog(output)
            # move parameters
            if remappedParam:
                for key, item in sorted(paramToTypes.iteritems()):
                    reg = 'p'+str(key)
                    mapping = parameterMap[reg]
                    # only doubles and longs use two
                    # registers, so use move-wide for them
                    if item == 'J' or item =='D':
                        output.write('     move-wide/16 '\
                            + mapping + ', ' + reg + '\n\n')
                    elif item =='L' or item == '[L':
                        output.write('     move-object/from16 '\
                            + mapping +', ' + reg +'\n\n')
                    else:
                        output.write('     move/from16 '\
                            + mapping +', ' + reg +'\n\n')
            if remappedParam:
                output.write(_remapParameters(line, parameterMap))
            else:
                output.write(line)
            return newReg, remappedParam, parameterMap, paramToTypes

        else:
            output.write(line)

def _injectMethodBody(source, output, newReg, remappedParam, parameterMap,
    appId, injectedMethods, methodsToParameters, paramToTypes):
    """Inject the body of current method."""
    depth = 0
    apiCalls = [[]]
    lineNumber = "-1"
    # logfile = open("injectlogfile.txt", "a")
    # logfile.write("injecting into method body of " + source.name + "\n")
    prevLine = ''
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
        elif not remappedParam:
            pattern = "v{}( |,|}}|$)".format(newReg)
            if re.search(re.compile(pattern), line) != None:
                # Line uses the first parameter for something.
                # Need to move the first parameter back into newReg before
                # executing the line
                moveLine = ""
                if paramToTypes[0] == 'L' or '[' in paramToTypes[0]:
                    moveLine = "    move-object/16 v{}, p0\n"
                elif paramToTypes[0] == 'J' or paramToTypes[0] == 'D':
                    moveLine = "    move-wide/16 v{}, p0\n"
                else:
                    moveLine = "    move/16 v{}, p0\n"
                moveLine = moveLine.format(newReg)
                output.write(moveLine)

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

        elif _lineHasInvoke(strip, appId, injectedMethods, methodsToParameters):
            name = _getNameFromInvoke(strip, appId)[len(appId):]
            msg = 'invoking subroutine l{} {}'.format(lineNumber, name)
            _addCustomLog(output, msg, newReg)

        elif strip.startswith('.line') or strip.startswith('return') \
            or strip.startswith('throw') \
            or strip.startswith('.end method'):
            _addAllLogAPI(output, apiCalls[0], newReg)
            apiCalls[0] = []

            if strip.startswith('.line'):
                lineNumber = strip.split()[-1]
            # if return or end of method, log an exit method message
            elif strip.startswith('return') or strip.startswith('throw'):
                _addMethodExitLog(output)
                # exitLogged = True
            elif 'return' not in prevLine and 'throw' not in prevLine \
                and '.end' not in prevLine:
                # for .end method
                _addMethodExitLog(output)

        output.write(line)
        if strip != '':
            prevLine = line
        if strip.startswith('.end method'):
            # logfile.close()
            return

def _injectFile(path, injectedMethods, methodsToParameters):
    """Inject a single file."""
    with open(path,'r') as source:
        # print ("Injecting into " + path)
        with open(path + outputExtension, 'w') as output:
            appId, className = _getPackageId(source)
            while _jumpToInjectedMethod(source, output, injectedMethods, className):
                newReg, remappedParam, parameterMap, paramsToTypes = _injectMethodPrologue(source,
                    output)
                _injectMethodBody(source, output, newReg, remappedParam,
                    parameterMap, appId, injectedMethods, methodsToParameters,
                    paramsToTypes)
            output.close()
        source.close()
    # overwrite the original file
    os.rename(path + outputExtension, path)

def _scanFile(path, methodsToInject, methodsToParameters):
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
                    methodParams = _getParametersFromMethodSignature(line)
                    if methodName in methodsToParameters:
                        methods = methodsToParameters[methodName]
                        methods.append(methodParams)
                    else:
                        methods = [methodParams]
                        methodsToParameters[methodName] = methods
                    methodsToInject.add(methodName)

        source.close()
        return

def _scan(path, filesToInject, methodsToInject, methodsToParameters):
    """Get the set of files and method to inject from a initial set of files."""
    # if path is an application file, it needs to be scanned and injected
    if os.path.isfile(path) and _isAppFile(path):
        _scanFile(path, methodsToInject, methodsToParameters)
        filesToInject.add(path)

   # recurse if path is a directory
    elif os.path.isdir(path):
        if path.endswith('/'):
            path += '*'
        else:
            path += '/*'

        files = glob.glob(path)

        for f in files:
            _scan(f, filesToInject, methodsToInject, methodsToParameters)


def main(argv):
    """Inject a set of files."""
    filesToInject = set()
    methodsToInject = set()
    methodsToParameters = {}
    # Clear log file
    # logfile = open("injectlogfile.txt", "w")
    # logfile.close()
    for path in argv:
        # check there are files to proccess
        files = glob.glob(path)
        if not files:
            raise RuntimeError('No files mathing path: ' + path)
        print 'inject.py: injecting files at: ' + path

        _scan(path, filesToInject, methodsToInject, methodsToParameters)

    for path in filesToInject:
        _injectFile(path, injectedMethods = methodsToInject,
            methodsToParameters = methodsToParameters)

if __name__ == "__main__":
    main(sys.argv[1:])
