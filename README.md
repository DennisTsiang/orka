## Synopsis
* Orka is a light-weigth energy profiling tool for Android applications, providing method and source-line level feeback to developpers about the energy usage of their code.
* Orka first injects the tested application and simulates a typical use case by running a monkeyrunner script provided by the user.


## Installation
* Before running Orka, the Android SDK, Python and Java need to be installed
on the machine.
* Two paths need to be exported:
    * $ORKA_HOME -- the path to the installation directory of Orka,
    * $ANDROID_HOME -- the path to the Android SDK.
* Orka can be ran on either an actual or a virtual device, running in the Android emulator. If using the emulator, the AVD to be tested needs to first be created in the AVD Manager, using x86 architecture.


## Execution
* Input is provided through the conf.ini file, which specifies the emulator to use (if any), the application to test, the monkeyrunner test script and the number of executions.
* When connected to an actual device or when an AVD is already launched, Orka will use this device and won't start the AVD specified in the configuration.
* Execute Orka by running './orka.sh', use '-h' option for more information.


## Files location
* Results are outputed in results_AVD/, where AVD is the name of the emulator provided in the configuration.
* The working/ directory contains Orka temporary files.


## Monkeyrunner
* The monkeyrecorder (located at testing/monkey_recorder.py) can be used to record test scenarios. Run the script in the terminal and use the mirored screen to record actions.
* Such monkey recorded text scripts can be played back if provided as input to the testing/monkey_player.py script.
