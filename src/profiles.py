def appendTestProfile(category):
    parameters = []
    if category == "Reddit Browsers":
        parameters.extend(["--Exploration-widgetActionDelay=100",
            "--Selectors-timeLimit=300000", "--Selectors-actionLimit=500"])
    else:
        parameters.extend(["--Exploration-widgetActionDelay=1000",
            "--Selectors-actionLimit=10"])
    return parameters
