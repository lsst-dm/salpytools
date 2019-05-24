# This file is part of salpytools
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (https://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import time
import sys
import threading
import logging
import salpytools.states as states
import inspect
import itertools
import importlib

"""
A Set of Python classes and tools to subscribe to LSST/SAL DDS topics
using the ts_sal generated libraries.  The the Main classes in the
module are:

- DDSController: Subscribe and acknowleges Commands for a Device
  (threaded)
- DDSSubcriber: Subscribe to Command/Telemetry/Event topics for a
  Device (threaded)
- DDSSend: Generates/send Telemetry, Events or Commands for a Device
  (non-threaded)
- DeviceState: Class Used by DDSController to store the state of the
  Commandable-Component/Device

"""

# Here we store the SAL classes and tools that we use to:
# - Control devices
# - Gather telemetry/events
# - Send Control commands (to sim OCS)
# NOTE: all import of SALPY_{moduleName} are done on the fly using the
# function load_SALPYlib()

spinner = itertools.cycle(['-', '/', '|', '\\'])

# Create a logger for all functions
LOGGER = logging.getLogger(__name__)


def load_SALPYlib(Device):
    """Trick to import modules dynamically as needed/depending on the Device we want"""

    # Make sure is not already loaded i.e. visible in globals
    try:
        SALPY_lib = globals()['SALPY_{}'.format(Device)]
        LOGGER.info('SALPY_{} is already in globals'.format(Device))
        return SALPY_lib
    except Exception:
        LOGGER.info('importing SALPY_{}'.format(Device))
        SALPY_lib = importlib.import_module("SALPY_{}".format(Device))
    else:
        raise ValueError("import SALPY_{}: failed".format(Device))
    # Update to make it visible elsewhere
    globals()['SALPY_{}'.format(Device)] = SALPY_lib
    return SALPY_lib


class DeviceState:

    """
    A Class to store the SCS (a.k.a Device). For now this is very
    rudimentary and written mostly to fullfil the needs of the
    HeaderService
    """

    def __init__(self, Device='atHeaderService', default_state='OFFLINE',
                 tsleep=0.5,
                 eventlist=['summaryState',
                            'settingVersions',
                            'settingsApplied',
                            'appliedSettingsMatchStart']):

        self.current_state = default_state
        self.tsleep = tsleep
        self.Device = Device

        LOGGER.info('{} Init beginning'.format(Device))
        LOGGER.info('Starting with default state: {}'.format(default_state))

        # Load (if not in globals already) SALPY_{deviceName} into class
        self.SALPY_lib = load_SALPYlib(self.Device)
        # Subscribe to all events in list
        self.subscribe_list(eventlist)
        # Get the enumeration of the states from the library
        try:
            self.load_state_enumeration()
        except Exception:
            LOGGER.warning("Cannot load state enumeration -- will use library instead")
            self.summaryState_enum = states.state_enumeration

    def load_state_enumeration(self):
        """
        Load up into dictionaries the SummaryState
        enumeration by getting the attributes of the shape
        'SALPY_ATCamera.SAL__STATE_DISABLED'
        """

        LOGGER.info('Loading up the SummaryState enumerations for {}'.format(self.Device))
        self.summaryState_enum = {}
        for name in states.state_names:

            # we get for example: SALPY_ATCamera.SAL__STATE_DISABLED
            self.summaryState_enum[name] = getattr(self.SALPY_lib, "SAL__STATE_{}"
                                                    .format(name.upper()))

            LOGGER.info("name: {0:10s} -- number: {1:2d}".format(name, self.summaryState_enum[name]))

    def subscribe_list(self, eventlist):
        # Subscribe to list of logEvents
        self.mgr = {}
        self.myData = {}
        self.logEvent = {}
        self.myData_keys = {}
        for eventname in eventlist:
            self.subscribe_logEvent(eventname)

    def send_logEvent(self, eventname, **kwargs):
        """Send logevent for an eventname"""
        # Populate myData object for keys across logevent
        kwargs.setdefault('timestamp', self.mgr[eventname].getCurrentTime())
        kwargs.setdefault('priority', 1)
        priority = int(self.myData[eventname].priority)

        # Populate myData with the default cases
        if eventname == 'summaryState':
            self.myData[eventname].summaryState = self.summaryState_enum[self.current_state]

        if eventname == 'settingsApplied':
            try:
                self.myData[eventname].settings = self.settings
            except Exception:
                LOGGER.warning("Could not extract 'settings' from state to reply the 'settingsApplied'")

        # Update myData from kwargs dict
        LOGGER.info('Updating myData object with kwargs')
        self.myData[eventname] = update_myData(self.myData[eventname], **kwargs)
        for key in self.myData_keys[eventname]:
            LOGGER.info('\t{}:{}'.format(key, getattr(self.myData[eventname], key)))

        LOGGER.info('Sending {}'.format(eventname))
        self.logEvent[eventname](self.myData[eventname], priority)
        LOGGER.info('Sent sucessfully {} Data Object'.format(eventname))
        for key in self.myData_keys[eventname]:
            LOGGER.info('\t{}:{}'.format(key, getattr(self.myData[eventname], key)))
        time.sleep(self.tsleep)
        return True

    def subscribe_logEvent(self, eventname):
        """
        Create a subscription for the {Device}_logevent_{eventnname}
        This step need to be done before we call send_logEvent
        """
        self.mgr[eventname] = getattr(self.SALPY_lib, 'SAL_{}'.format(self.Device))()
        self.mgr[eventname].salEventPub("{}_logevent_{}".format(self.Device, eventname))
        self.logEvent[eventname] = getattr(self.mgr[eventname], 'logEvent_{}'.format(eventname))
        self.myData[eventname] = getattr(
            self.SALPY_lib, '{}_logevent_{}C'.format(self.Device, eventname))()

        self.myData_keys[eventname] = [a[0] for a in inspect.getmembers(
            self.myData[eventname]) if not(a[0].startswith('__') and a[0].endswith('__'))]
        LOGGER.info('Initializing: {}_logevent_{}'.format(self.Device, eventname))

    def get_current_state(self):
        """Function to get the current state"""
        return self.current_state


class DDSController(threading.Thread):

    """
    Class to subscribe and react to Commands for a Device.
    This class is very similar to DDSSubcriber, but the difference is
    that this one can send the acks to the Commands.
    """

    def __init__(self, command, Device='atHeaderService', topic=None, threadID='1', tsleep=0.5, State=None):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.Device = Device
        self.command = command
        self.COMMAND = self.command.upper()
        # The topic:
        if not topic:
            self.topic = "{}_command_{}".format(Device, command)
        else:
            self.topic = topic
        self.tsleep = tsleep
        self.daemon = True
        self.State = State

        # Store to which state this command is going to move up, using the states.next_state dictionary
        self.next_state = states.next_state[self.COMMAND]

        # Subscribe
        self.subscribe()

    def subscribe(self):

        # This section does the equivalent of:
        # self.mgr = SALPY_tcs.SAL_tcs()
        # The steps are:
        # - 'figure out' the SALPY_xxxx module name
        # - find the library pointer using globals()
        # - create a mananger
        # Here we do the equivalent of:
        # mgr.salProcessor("atHeaderService_command_EnterControl")

        self.newControl = False

        # Load (if not in globals already) SALPY_{deviceName} into class
        self.SALPY_lib = load_SALPYlib(self.Device)
        self.mgr = getattr(self.SALPY_lib, 'SAL_{}'.format(self.Device))()
        self.mgr.salProcessor(self.topic)
        self.myData = getattr(self.SALPY_lib, self.topic+'C')()
        LOGGER.info("{} controller ready for topic: {}".format(self.Device, self.topic))

        # We use getattr to get the equivalent of for our accept and ack command
        # mgr.acceptCommand_EnterControl()
        # mgr.ackCommand_EnterControl
        self.mgr_acceptCommand = getattr(self.mgr, 'acceptCommand_{}'.format(self.command))
        self.mgr_ackCommand = getattr(self.mgr, 'ackCommand_{}'.format(self.command))

    def run(self):
        self.run_command()

    def run_command(self):
        while True:
            cmdId = self.mgr_acceptCommand(self.myData)
            if cmdId > 0:
                self.reply_to_transition(cmdId)
                self.newControl = True
            time.sleep(self.tsleep)

    def reply_to_transition(self, cmdId):

        # Check if valid transition
        if validate_transition(self.State.current_state, self.next_state):
            # Send the ACK
            msg = "Successful transition from: {} --> {}".format(self.State.current_state,
                                                                 self.next_state)
            self.mgr_ackCommand(cmdId, self.SALPY_lib.SAL__CMD_COMPLETE, 0, msg)
            # Update the current state
            self.State.current_state = self.next_state

            if self.COMMAND == 'ENTERCONTROL':
                self.State.send_logEvent("settingVersions", recommendedSettingsVersion='normal')
                self.State.send_logEvent('summaryState')
            elif self.COMMAND == 'START':
                # TODO: use either 'myData.configure' or
                # 'myData.settingsToApply'. The XML keeps changing
                #
                # Here we extract 'myData.configure' or
                # 'myData.settingsToApply' for START, eventually we
                # will apply the setting for this configuration.
                try:
                    LOGGER.info("From {} received configure: {}".format(
                        self.COMMAND, self.myData.configure))
                except Exception:
                    LOGGER.info("From {} received configure: {}".format(
                        self.COMMAND, self.myData.settingsToApply))
                # Here we should apply the setting in the future
                self.State.send_logEvent('settingsApplied')
                self.State.send_logEvent('appliedSettingsMatchStart',
                                         appliedSettingsMatchStartIsTrue=1)
                self.State.send_logEvent('summaryState')
            else:
                self.State.send_logEvent('summaryState')
        else:
            msg = "WARNING: Invalid Transition from: {} --> {}".format(self.State.current_state,
                                                                       self.next_state)
            LOGGER.warning(msg)
            # Send the ACK
            self.mgr_ackCommand(cmdId, self.SALPY_lib.SAL__CMD_NOPERM, 0, msg)


def validate_transition(current_state, new_state):
    """
    Stand-alone function to validate transition. It returns true/false
    """
    current_index = states.state_enumeration[current_state]
    new_index = states.state_enumeration[new_state]
    transition_is_valid = states.state_matrix[current_index][new_index]
    if transition_is_valid:
        LOGGER.info("Transition from: {} --> {} is VALID".format(current_state, new_state))
    else:
        LOGGER.info("Transition from: {} --> {} is INVALID".format(current_state, new_state))
    return transition_is_valid


class DDSSubcriber(threading.Thread):

    """ Class to Subscribe to Telemetry, it could a Command (discouraged), Event or Telemetry"""

    def __init__(self, Device, topic, threadID='1', Stype='Telemetry', tsleep=0.01, timeout=3600, nkeep=100):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.Device = Device
        self.topic = topic
        self.tsleep = tsleep
        self.Stype = Stype
        self.timeout = timeout
        self.nkeep = nkeep
        self.daemon = True
        self.subscribe()

    def subscribe(self):

        # This section does the equivalent of:
        # self.mgr = SALPY_tcs.SAL_tcs()
        # The steps are:
        # - 'figure out' the SALPY_xxxx Device name
        # - find the library pointer using globals()
        # - create a mananger

        self.newTelem = False
        self.newEvent = False

        # Load (if not in globals already) SALPY_{deviceName} into class
        self.SALPY_lib = load_SALPYlib(self.Device)
        self.mgr = getattr(self.SALPY_lib, 'SAL_{}'.format(self.Device))()

        if self.Stype == 'Telemetry':
            self.myData = getattr(self.SALPY_lib, '{}_{}C'.format(self.Device, self.topic))()
            self.mgr.salTelemetrySub("{}_{}".format(self.Device, self.topic))
            # Generic method to get for example: self.mgr.getNextSample_kernel_FK5Target
            self.getNextSample = getattr(self.mgr, "getNextSample_{}".format(self.topic))
            LOGGER.info("{} subscriber ready for Device:{} topic:{}".format(
                self.Stype, self.Device, self.topic))
        elif self.Stype == 'Event':
            self.myData = getattr(
                self.SALPY_lib, '{}_logevent_{}C'.format(self.Device, self.topic))()
            self.mgr.salEventSub("{}_logevent_{}".format(self.Device, self.topic))
            # Generic method to get for example: self.mgr.getEvent_startIntegration(event)
            self.getEvent = getattr(self.mgr, 'getEvent_{}'.format(self.topic))
            LOGGER.info("{} subscriber ready for Device:{} topic:{}".format(
                self.Stype, self.Device, self.topic))
        elif self.Stype == 'Command':
            self.myData = getattr(self.SALPY_lib, '{}_command_{}C'.format(self.Device, self.topic))()
            self.mgr.salProcessor("{}_command_{}".format(self.Device, self.topic))
            # Generic method to get for example: self.mgr.acceptCommand_takeImages(event)
            self.acceptCommand = getattr(self.mgr, 'acceptCommand_{}'.format(self.topic))
            LOGGER.info("{} subscriber ready for Device:{} topic:{}".format(
                self.Stype, self.Device, self.topic))

    def run(self):
        """ The run method for the threading"""
        self.myDatalist = []
        if self.Stype == 'Telemetry':
            self.newTelem = False
            self.run_Telem()
        elif self.Stype == 'Event':
            self.newEvent = False
            self.run_Event()
        elif self.Stype == 'Command':
            self.newCommand = False
            self.run_Command()
        else:
            raise ValueError("Stype=%s not defined\n" % self.Stype)

    def run_Telem(self):
        while True:
            retval = self.getNextSample(self.myData)
            if retval == 0:
                self.myDatalist.append(self.myData)
                self.myDatalist = self.myDatalist[-self.nkeep:]  # Keep only nkeep entries
                self.newTelem = True
            time.sleep(self.tsleep)
        return

    def run_Event(self):
        self.timeoutEvent = False
        while True:
            retval = self.getEvent(self.myData)
            if retval == 0:
                self.myDatalist.append(self.myData)
                self.myDatalist = self.myDatalist[-self.nkeep:]  # Keep only nkeep entries
                self.newEvent = True
                # Capture the current timeStamp only if defined as an attribute!
                if hasattr(self.myData, 'timeStamp'):
                    self.timeStamp = self.myData.timeStamp
            time.sleep(self.tsleep)
        return

    def run_Command(self):
        while True:
            self.cmdId = self.acceptCommand(self.myData)
            if self.cmdId > 0:
                self.myDatalist.append(self.myData)
                self.myDatalist = self.myDatalist[-self.nkeep:]  # Keep only nkeep entries
                self.newCommand = True
            time.sleep(self.tsleep)
        return

    def getCurrent(self, getNone=False):
        if len(self.myDatalist) > 0:
            Current = self.myDatalist[-1]
            self.newTelem = False
            self.newEvent = False
        else:
            if getNone:
                Current = None
            else:
                Current = self.myData
            msg = "No value received for topic: '{}'".format(self.topic)
            LOGGER.warning(msg)
        return Current

    def getCurrentTelemetry(self):
        return self.getCurrent()

    def getCurrentEvent(self):
        return self.getCurrent()

    def getCurrentCommand(self):
        return self.getCurrent()

    def waitEvent(self, tsleep=None, timeout=None, after_timeStamp=-1):
        """
        Loop while waiting for a new event.

        This function waits until the class gets a new event via the
        variable self.newEvent. self.newEvent is controlled by the run_Event function.
        - Once self.newEvent changes to True, the function makes sure that the timeStamp
        in this new event happened AFTER the after_timeStamp time set in the function call. This
        ensures that no rogue newEvent triggered the wait. If this is a bona-fide new Event, then we
        break from the loop. By default after_timeStamp=-1, to make sure dtime is positive in case
        that after_timeStamp is not defined.
        - If the time inside the wait loop exceeds the timeout set time, then the function breaks
        from the loop and returns self.timeoutEvent=True and self.newEvent=False
        """
        if not tsleep:
            tsleep = self.tsleep
        if not timeout:
            timeout = self.timeout

        t0 = time.time()
        self.timeoutEvent = False

        while True:
            sys.stdout.flush()
            sys.stdout.write("Waiting for {} event.. [{}]".format(self.topic, next(spinner)))
            sys.stdout.write('\r')
            if self.newEvent:
                # Make sure that self.newEvent happens AFTER the time stamp requested time
                rogueEvent = self.check_rogueEvent(after_timeStamp)
                if rogueEvent:
                    LOGGER.warning("Received Rogue {} Event -- will keep waiting".format(self.topic))
                    self.newEvent = False
                else:
                    LOGGER.info("Received New {} Event -- stop waiting".format(self.topic))
                    break
            elif time.time() - t0 > timeout:
                LOGGER.warning("Timeout waiting for Event %s" % self.topic)
                self.newEvent = False
                self.timeoutEvent = True
                break
            else:
                self.timeoutEvent = False
            time.sleep(tsleep)

        return self.newEvent

    def check_rogueEvent(self, after_timeStamp):
        """
        Check for rogue events that occurrs in the past.
        Make sure that self.newEvent happens AFTER the time stamp requested time.
        If after_timeStamp is < 0, we do not check for rogue events
        """
        # Only check if after_timeStamp is > 0
        if after_timeStamp < 0:
            rogueEvent = False
            return rogueEvent
        # Make sure that the Event has the timeStamp attribute
        if hasattr(self, 'timeStamp'):
            # Make sure that self.newEvent happens AFTER the time stamp requested time
            dtime = self.timeStamp - after_timeStamp
            if dtime < 0:
                rogueEvent = True
            else:
                rogueEvent = False
        else:
            LOGGER.warning("New Event: {} has not timeStamp".format(self.topic))
            LOGGER.warning("Cannot check for rogue timeStamp, proceeding with trepidation")
            rogueEvent = False
        return rogueEvent

    def resetEvent(self):
        """ Simple function to set it back"""
        self.newEvent = False


class DDSSend(threading.Thread):

    """
    Class to generate/send Telemetry, Events or Commands.
    In the case of a command, the class instance cannot be
    re-used.
    For Events/Telemetry, the same object can be re-used for a given Device,
    """

    def __init__(self, Device, sleeptime=1, timeout=5, threadID=1):
        threading.Thread.__init__(self)
        self.daemon = True
        self.threadID = threadID
        self.sleeptime = sleeptime
        self.timeout = timeout
        self.Device = Device
        LOGGER.info("Loading Device: {}".format(self.Device))
        # Load SALPY_lib into the class
        self.SALPY_lib = load_SALPYlib(self.Device)

    def run(self):
        """ Function for threading"""
        self.waitForCompletion_Command()

    def get_mgr(self):
        # We get the equivalent of:
        #  mgr = SALPY_atHeaderService.SAL_atHeaderService()
        mgr = getattr(self.SALPY_lib, 'SAL_{}'.format(self.Device))()
        return mgr

    def send_Command(self, cmd, **kwargs):
        """ Send a Command to a Device"""
        timeout = int(kwargs.pop('timeout', self.timeout))
        # sleeptime = kwargs.pop('sleeptime', self.sleeptime)
        wait_command = kwargs.pop('wait_command', False)

        # Get the mgr handle
        mgr = self.get_mgr()
        mgr.salProcessor("{}_command_{}".format(self.Device, cmd))
        # Get the myData object
        myData = getattr(self.SALPY_lib, '{}_command_{}C'.format(self.Device, cmd))()
        LOGGER.info('Updating myData object with kwargs')
        myData = update_myData(myData, **kwargs)
        # Make it visible outside
        self.myData = myData
        self.cmd = cmd
        self.timeout = timeout
        # For a Command we need the functions:
        # 1) issueCommand
        # 2) waitForCompletion -- this can be run separately
        self.issueCommand = getattr(mgr, 'issueCommand_{}'.format(cmd))
        self.waitForCompletion = getattr(mgr, 'waitForCompletion_{}'.format(cmd))
        LOGGER.info("Issuing command: {}".format(cmd))
        self.cmdId = self.issueCommand(myData)
        self.cmdId_time = time.time()
        if wait_command:
            LOGGER.info("Will wait for Command Completion")
            self.waitForCompletion_Command()
        else:
            LOGGER.info("Will NOT wait Command Completion")
        return self.cmdId

    def waitForCompletion_Command(self):
        LOGGER.info("Wait {} sec for Completion: {}".format(self.timeout, self.cmd))
        retval = self.waitForCompletion(self.cmdId, self.timeout)
        LOGGER.info("Done: {}".format(self.cmd))
        return retval

    def ackCommand(self, cmd, cmdId, ack=None, msg=None):
        """ Just send the ACK for a command, it need the cmdId as input"""

        # Assume ack is OK unless otherwise stated
        if not ack:
            ack = self.SALPY_lib.SAL__CMD_COMPLETE
        if not msg:
            msg = "Done : OK"
        LOGGER.info("Sending ACK for Id: {} for Command: {}".format(cmdId, cmd))
        mgr = self.get_mgr()
        mgr.salProcessor("{}_command_{}".format(self.Device, cmd))
        ackCommand = getattr(mgr, 'ackCommand_{}'.format(cmd))
        ackCommand(cmdId, ack, 0, msg)

    def acceptCommand(self, cmd):
        mgr = self.get_mgr()
        mgr.salProcessor("{}_command_{}".format(self.Device, cmd))
        acceptCommand = getattr(mgr, 'acceptCommand_{}'.format(cmd))
        myData = getattr(self.SALPY_lib, '{}_command_{}C'.format(self.Device, cmd))()
        while True:
            cmdId = acceptCommand(myData)
            if cmdId > 0:
                time.sleep(1)
                break
        cmdId = acceptCommand(myData)
        LOGGER.info("Accpeting cmdId: {} for Command: {}".format(cmdId, cmd))
        return cmdId

    def send_Event(self, event, **kwargs):
        """ Send an Event from a Device"""

        sleeptime = kwargs.pop('sleep_time', self.sleeptime)
        priority = kwargs.get('priority', 1)

        myData = getattr(self.SALPY_lib, '{}_logevent_{}C'.format(self.Device, event))()
        LOGGER.info('Updating myData object with kwargs')
        myData = update_myData(myData, **kwargs)
        # Make it visible outside
        self.myData = myData
        # Get the logEvent object to send myData
        mgr = self.get_mgr()
        # name = "{}_logevent_{}".format(self.Device, event)
        mgr.salEventPub("{}_logevent_{}".format(self.Device, event))
        logEvent = getattr(mgr, 'logEvent_{}'.format(event))
        LOGGER.info("Sending Event: {}".format(event))
        logEvent(myData, priority)
        LOGGER.info("Done: {}".format(event))
        time.sleep(sleeptime)

    def send_Telemetry(self, topic, **kwargs):
        """ Send an Telemetry from a Device"""

        sleeptime = kwargs.pop('sleep_time', self.sleeptime)
        # Get the myData object
        myData = getattr(self.SALPY_lib, '{}_{}C'.format(self.Device, topic))()
        LOGGER.info('Updating myData object with kwargs')
        myData = update_myData(myData, **kwargs)
        # Make it visible outside
        self.myData = myData
        # Get the Telemetry object to send myData
        mgr = self.get_mgr()
        mgr.salTelemetryPub("{}_{}".format(self.Device, topic))
        putSample = getattr(mgr, 'putSample_{}'.format(topic))
        LOGGER.info("Sending Telemetry: {}".format(topic))
        putSample(myData)
        LOGGER.info("Done: {}".format(topic))
        time.sleep(sleeptime)

    def get_myData(self):
        """ Make a dictionary representation of the myData C objects"""
        myData_dic = {}
        myData_keys = [a[0] for a in inspect.getmembers(self.myData) if not(
            a[0].startswith('__') and a[0].endswith('__'))]
        for key in myData_keys:
            myData_dic[key] = getattr(self.myData, key)
        return myData_dic


def update_myData(myData, **kwargs):
    """ Updating myData with kwargs """
    myData_keys = [a[0] for a in inspect.getmembers(myData) if not(
        a[0].startswith('__') and a[0].endswith('__'))]
    for key in kwargs:
        if key in myData_keys:
            setattr(myData, key, kwargs.get(key))
        else:
            LOGGER.info('key {} not in myData'.format(key))
    return myData


def command_sequencer(commands, Device='ATHeaderService', wait_time=1, sleep_time=3):
    """
    Stand-alone function to send a sequence of OCS Commands
    """

    # We get the equivalent of:
    #  mgr = SALPY_atHeaderService.SAL_atHeaderService()
    # Load (if not in globals already) SALPY_{deviceName}
    SALPY_lib = load_SALPYlib(Device)

    mgr = getattr(SALPY_lib, 'SAL_{}'.format(Device))()
    myData = {}
    issueCommand = {}
    waitForCompletion = {}
    for cmd in commands:
        myData[cmd] = getattr(SALPY_lib, '{}_command_{}C'.format(Device, cmd))()
        issueCommand[cmd] = getattr(mgr, 'issueCommand_{}'.format(cmd))
        waitForCompletion[cmd] = getattr(mgr, 'waitForCompletion_{}'.format(cmd))
        # If Start we send some non-sense value
        if cmd == 'start' or cmd == 'Start':
            myData[cmd].settingsToApply = 'normal'

    for cmd in commands:
        LOGGER.info("Issuing command: {}".format(cmd))
        LOGGER.info("Wait for Completion: {}".format(cmd))
        cmdId = issueCommand[cmd](myData[cmd])
        retval = waitForCompletion[cmd](cmdId, wait_time)
        # Report if timed out and get the proper code
        if retval == SALPY_lib.SAL__CMD_NOACK:
            LOGGER.info("Command: {} timed out".format(cmd))
        LOGGER.info("Done: {}".format(cmd))
        time.sleep(sleep_time)

    mgr.salShutdown()
    return


def purge_command(device, command, sleep=0.5):
    SALPY_lib = load_SALPYlib(device)
    mgr = getattr(SALPY_lib, 'SAL_{}'.format(device))()
    mgr.salProcessor("{}_command_{}".format(device, command))
    LOGGER.info("Subscribing to: {}_command_{}".format(device, command))
    time.sleep(sleep)
    mgr.salShutdown()
    LOGGER.info("Purged: {}".format(command))
    LOGGER.info("--------------------------")
    return


def purge_event(device, event, sleep=0.5):
    SALPY_lib = load_SALPYlib(device)
    mgr = getattr(SALPY_lib, 'SAL_{}'.format(device))()
    mgr.salEventSub("{}_logevent_{}".format(device, event))
    LOGGER.info("Subscribing to: {}_logevent_{}".format(device, event))
    time.sleep(sleep)
    mgr.salShutdown()
    LOGGER.info("Purged: {}".format(event))
    LOGGER.info("--------------------------")
    return


def purge_telem(device, telem, sleep=0.5):
    SALPY_lib = load_SALPYlib(device)
    mgr = getattr(SALPY_lib, 'SAL_{}'.format(device))()
    mgr.salTelemetrySub("{}_{}".format(device, telem))
    LOGGER.info("Subscribing to: {}_{}".format(device, telem))
    time.sleep(sleep)
    mgr.salShutdown()
    LOGGER.info("Purged: {}".format(telem))
    LOGGER.info("--------------------------")
    return


def purge_csc(csc_name, topic_name, ctype='command', sleep=0.5):

    if ctype == 'command':
        purge_command(csc_name, topic_name, sleep=sleep)
    elif ctype == 'event':
        purge_event(csc_name, topic_name, sleep=sleep)
    elif ctype == 'telem':
        purge_telem(csc_name, topic_name, sleep=sleep)
    else:
        print("WARNING: CSC type not recognize, [command,event,telem]")
    return
