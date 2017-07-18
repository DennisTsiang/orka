"""Contain the Routine class."""

class Routine(object):
    """
    Represent the behaviour of a routine recorded in the logs.
    """

    def __init__(self, name):
        """
        Create a new instance of Routine with given name, no calls and no API.

        Keyword arguments:
        name: the name of the routine assiocated with this new instance

        apiCalls and apiCosts map line numbers with dicts mapping apis to values
            (number of calls or costs)
        subroutines map line numbers with subroutines called at these lines
        """
        self.name = name
        self.calls = .0
        self.apiCalls = {}
        self.apiCosts = {}
        self.subroutines = {}

    def addCall(self):
        """Add a call to current instance."""
        self.calls += 1

    def addApi(self, apiName, line = 0):
        """
        Add an API call to current instance.

        Keyword arguments:
        apiName -- name of the called API
        line -- line number of the source code where the call occured (default 0)
        """
        # if needed, create dict entry for this line
        if not self.apiCalls.has_key(line):
            self.apiCalls[line] = {}

        apiCalls = self.apiCalls[line]

        # add call for this API in this line
        if not apiCalls.has_key(apiName):
            apiCalls[apiName] = 1.0
        else:
            apiCalls[apiName] += 1

    def addSubroutine(self, lineNumber, subroutine):
        """
        Add given subroutine at given line.

        Keyword arguments:
        lineNumber -- line number where the subroutine is called
        subroutine -- subroutine's name
        """
        self.subroutines[lineNumber] = subroutine

    def toJson(self):
        """Create a JSON object from the current instance."""
        objDict = {}
        objDict['name'] = self.name
        objDict['calls'] = self.calls
        objDict['apiCalls'] = self.apiCalls
        objDict['apiCosts'] = self.apiCosts
        objDict['subroutines'] = self.subroutines

        return objDict

    def buildApiCosts(self, refApiCosts, unknownApis = None):
        """
        Compute the cost of each line.

        Keyword arguments:
        refApiCosts -- reference cost of API calls
        unknownApis -- set used to store the unknown APIs found during the
            analysis (default None)
        """
        # if needed, create the set of unknown apis
        if not unknownApis:
            unknownApis = set()

        # iterate over the lines
        for lineNumber in self.apiCalls.keys():
            self.apiCosts[lineNumber] = 0
            line = self.apiCalls[lineNumber]

            # iterate over the apis
            for api in line.keys():
                if refApiCosts.has_key(api):
                    self.apiCosts[lineNumber] += line[api] * refApiCosts[api]
                else:
                    unknownApis.add(api)

        return unknownApis

    def normalize(self, norm):
        """
        Normalize current instance by given factor.

        Keyword arguments:
        norm -- normalisation factor, typically the number of runs
        """
        self.calls /= norm
        for line in self.apiCalls.values():
            for apiName in line.keys():
                line[apiName] /= norm

    def _getTotalCost(self):
        """Compute the total cost of associated routine."""
        total = .0
        for value in self.apiCosts.values():
            total += value
        return total

    def getAverageCost(self):
        """Compute the average cost per run of associated routine."""
        return self._getTotalCost() / self.calls

    def generateLineFeedback(self):
        """Generate the source line level feedback for this routine."""
        output = []
        output.append("method {}, Average cost: {}, Calls: {}\n".format(
            self.name, self.getAverageCost(), self.calls))

        # Compute the relative cost of each line in percent
        relativeCosts = self.apiCosts.copy()
        totalCost = self._getTotalCost()
        for line in relativeCosts.keys():
            relativeCosts[line] *= 100.0 / totalCost

        # iterate over each line
        lines = self.apiCosts.keys()
        lines.sort()
        for line in lines:
            if relativeCosts[line] == 0:
                continue

            output.append("{:10.2f}% l{}".format(relativeCosts[line],
                str(line), self.calls))
            if line > 0:
                # if known, add the name of corresponding subroutine
                if line in self.subroutines.keys():
                    name = self.subroutines[line]
                else:
                    name = ', '.join(self.apiCalls[line].keys())
                output.append('    calling ' + name)
            output.append('\n')

        output.append("\n")

        out = ''.join(output)
        return out
