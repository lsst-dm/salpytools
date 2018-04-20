
import time
import sys
import threading
import logging
import HeaderService.hutils as hutils
import HeaderService.states as states
import inspect
import copy


"""
Here we store the SAL classes and tools that we use to:
 - Control devices
 - Gather telemetry/events
 - Send Control commands (to sim OCS)
 

NOTE: all import of SALPY_{moduleName} are done on the fly using the fuction load_SALPYlib()
"""

spinner = hutils.spinner
LOGGER = hutils.create_logger(level=logging.NOTSET,name=__name__)
SAL__CMD_COMPLETE=303

def load_SALPYlib(Device):
    '''Trick to import modules dynamically as needed/depending on the Device we want'''

    # Make sure is not already loaded i.e. visible in globals
    try:
        SALPY_lib = globals()['SALPY_{}'.format(Device)]
        LOGGER.info('SALPY_{} is already in globals'.format(Device))
        return SALPY_lib
    except:
        LOGGER.info('importing SALPY_{}'.format(Device))
        exec "import SALPY_{}".format(Device)
    else:
        raise ValueError("import SALPY_{}: failed".format(Device))
    SALPY_lib = locals()['SALPY_{}'.format(Device)]
    # Update to make it visible elsewhere -- not sure if this works
    globals()['SALPY_{}'.format(Device)] = SALPY_lib
    return SALPY_lib

class DeviceState:

    def __init__(self, Device='atHeaderService',default_state='OFFLINE',
                 tsleep=0.5,
                 eventlist = ['SummaryState',
                              'SettingVersions',
                              'RejectedCommand',
                              'SettingsApplied',
                              'AppliedSettingsMatchStart'] ):

        self.current_state = default_state
        self.tsleep = tsleep
        self.Device = Device
        
        LOGGER.info('{} Init beginning'.format(Device))
        LOGGER.info('Starting with default state: {}'.format(default_state))

        # Load (if not in globals already) SALPY_{deviceName} into class
        self.SALPY_lib = load_SALPYlib(self.Device)
        # Subscribe to all events in list
        self.subscribe_list(eventlist)

    def subscribe_list(self,eventlist):
        # Subscribe to list of logEvents
        self.mgr = {}
        self.myData = {}
        self.logEvent = {}
        self.myData_keys = {}
        for eventname in eventlist:
            self.subscribe_logEvent(eventname)

    def send_logEvent(self,eventname,**kwargs):
        ''' Send logevent for an eventname'''
        # Populate myData object for keys across logevent
        self.myData[eventname].timestamp = kwargs.pop('timestamp',time.time())
        self.myData[eventname].priority  = kwargs.pop('priority',1)
        priority = int(self.myData[eventname].priority)

        # Populate myData with the default cases
        if eventname == 'SummaryState':
            self.myData[eventname].summaryState = states.state_enumeration[self.current_state] 
        if eventname == 'RejectedCommand':
            rejected_state = kwargs.get('rejected_state')
            next_state = states.next_state[rejected_state]
            self.myData[eventname].commandValue = states.state_enumeration[next_state] # CHECK THIS OUT
            self.myData[eventname].detailedState = states.state_enumeration[self.current_state] 

        # Override from kwargs
        for key in kwargs:
            setattr(self.myData[eventname],key,kwargs.get(key))

        LOGGER.info('Sending {}'.format(eventname))
        self.logEvent[eventname](self.myData[eventname], priority)
        LOGGER.info('Sent sucessfully {} Data Object'.format(eventname))
        for key in self.myData_keys[eventname]:
            LOGGER.info('\t{}:{}'.format(key,getattr(self.myData[eventname],key)))
        time.sleep(self.tsleep)
        return True

    def subscribe_logEvent(self,eventname):
        '''
        Create a subscription for the {Device}_logevent_{eventnname}
        This step need to be done before we call send_logEvent
        '''
        self.mgr[eventname] = getattr(self.SALPY_lib, 'SAL_{}'.format(self.Device))()
        self.mgr[eventname].salEvent("{}_logevent_{}".format(self.Device,eventname))
        self.logEvent[eventname] = getattr(self.mgr[eventname],'logEvent_{}'.format(eventname))
        self.myData[eventname] = getattr(self.SALPY_lib,'{}_logevent_{}C'.format(self.Device,eventname))()
            
        self.myData_keys[eventname] = [a[0] for a in inspect.getmembers(self.myData[eventname]) if not(a[0].startswith('__') and a[0].endswith('__'))]
        LOGGER.info('Initializing: {}_logevent_{}'.format(self.Device,eventname))
        
    def get_current_state(self):
        '''Function to get the current state'''
        return self.current_state


class DDSController(threading.Thread):
    
    def __init__(self, command, module='atHeaderService', topic=None, threadID='1', tsleep=0.5, State=None):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.module = module
        self.command  = command
        self.COMMAND = self.command.upper()
        # The topic:
        if not topic:
            self.topic = "{}_command_{}".format(module,command)
        else:
            self.topic  = topic
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

        # Get the mgr
        #SALPY_lib_name = 'SALPY_{}'.format(self.module)
        #SALPY_lib = globals()[SALPY_lib_name]
        SALPY_lib = globals()['SALPY_{}'.format(self.module)]
        self.mgr = getattr(SALPY_lib, 'SAL_{}'.format(self.module))()
        self.mgr.salProcessor(self.topic)
        self.myData = getattr(SALPY_lib,self.topic+'C')()
        LOGGER.info("{} controller ready for topic: {}".format(self.module,self.topic))

        # We use getattr to get the equivalent of for our accept and ack command
        # mgr.acceptCommand_EnterControl()
        # mgr.ackCommand_EnterControl
        self.mgr_acceptCommand = getattr(self.mgr,'acceptCommand_{}'.format(self.command))
        self.mgr_ackCommand = getattr(self.mgr,'ackCommand_{}'.format(self.command))

    def run(self):
        self.run_command()

    def run_command(self):
        while True:
            cmdId = self.mgr_acceptCommand(self.myData)
            if cmdId > 0:
                self.reply_to_transition(cmdId)
                self.newControl = True
            time.sleep(self.tsleep)

    def reply_to_transition(self,cmdId):

        # Check if valid transition
        if validate_transition(self.State.current_state, self.next_state):
            # Send the ACK
            self.mgr_ackCommand(cmdId, SAL__CMD_COMPLETE, 0, "Done : OK");
            # Update the current state
            self.State.current_state = self.next_state

            if self.COMMAND == 'ENTERCONTROL':
                self.State.send_logEvent("SettingVersions",recommendedSettingsVersion='blah')
                self.State.send_logEvent('SummaryState')
            elif self.COMMAND == 'START':
                # Extract 'myData.configure' for START, eventually we
                # will apply the setting for this configuration, for now we
                LOGGER.info("From {} received configure: {}".format(self.COMMAND,self.myData.configure))
                # Here we should apply the setting in the future
                self.State.send_logEvent('SettingsApplied')
                self.State.send_logEvent('AppliedSettingsMatchStart',appliedSettingsMatchStartIsTrue=1)
                self.State.send_logEvent('SummaryState')
            else:
                self.State.send_logEvent('SummaryState')
        else:
            LOGGER.info("WARNING: INVALID TRANSITION from {} --> {}".format(self.State.current_state, self.next_state))
            self.State.send_logEvent('RejectedCommand',rejected_state=self.COMMAND)


def validate_transition(current_state, new_state):
    """
    Stand-alone function to validate transition. It returns true/false
    """
    current_index = states.state_enumeration[current_state]
    new_index = states.state_enumeration[new_state]
    transition_is_valid = states.state_matrix[current_index][new_index]
    if transition_is_valid:
        LOGGER.info("Transition from {} --> {} is VALID".format(current_state, new_state))
    else:
        LOGGER.info("Transition from {} --> {} is INVALID".format(current_state, new_state))
    return transition_is_valid 


class DDSSubcriber(threading.Thread):

    def __init__(self, Device, topic, threadID='1', Stype='Telemetry',tsleep=0.01,timeout=3600,nkeep=100):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.Device = Device
        self.topic  = topic
        self.tsleep = tsleep
        self.Stype  = Stype
        self.timeout = timeout
        self.nkeep   = nkeep
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

        if self.Stype=='Telemetry':
            self.myData = getattr(SALPY_lib,'{}_{}C'.format(self.Device,self.topic))()
            self.mgr.salTelemetrySub("{}_{}".format(self.Device,self.topic))
            # Generic method to get for example: self.mgr.getNextSample_kernel_FK5Target
            self.getNextSample = getattr(self.mgr,"getNextSample_{}".format(self.topic))
            LOGGER.info("{} subscriber ready for Device:{} topic:{}".format(self.Stype,self.Device,self.topic))
        elif self.Stype=='Event':
            self.myData = getattr(self.SALPY_lib,'{}_logevent_{}C'.format(self.Device,self.topic))()
            self.mgr.salEvent("{}_logevent_{}".format(self.Device,self.topic))
            # Generic method to get for example: self.mgr.getEvent_startIntegration(event)
            self.getEvent = getattr(self.mgr,'getEvent_{}'.format(self.topic))
            LOGGER.info("{} subscriber ready for Device:{} topic:{}".format(self.Stype,self.Device,self.topic))
        elif self.Stype=='Command':
            self.myData = getattr(SALPY_lib,'{}_command_{}C'.format(self.Device,self.topic))()
            self.mgr.salProcessor("{}_command_{}".format(self.Device,self.topic))
            # Generic method to get for example: self.mgr.acceptCommand_takeImages(event)
            self.acceptCommand = getattr(self.mgr,'acceptCommand_{}'.format(self.topic))
            LOGGER.info("{} subscriber ready for Device:{} topic:{}".format(self.Stype,self.Device,self.topic))
            
    def run(self):
        ''' The run method for the threading'''
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
                self.myDatalist = self.myDatalist[-self.nkeep:] # Keep only nkeep entries
                self.newTelem = True
            time.sleep(self.tsleep)
        return 
    
    def run_Event(self):
        while True:
            retval = self.getEvent(self.myData)
            if retval == 0:
                self.myDatalist.append(self.myData)
                self.myDatalist = self.myDatalist[-self.nkeep:] # Keep only nkeep entries
                self.newEvent = True
            time.sleep(self.tsleep)
        return 
    def run_Command(self):
        while True:
            self.cmdId = self.acceptCommand(self.myData)
            if self.cmdId > 0:
                self.myDatalist.append(self.myData)
                self.myDatalist = self.myDatalist[-self.nkeep:] # Keep only nkeep entries
                self.newCommand = True
            time.sleep(self.tsleep)
        return 

    def getCurrent(self):
        if len(self.myDatalist) > 0:
            Current = self.myDatalist[-1]
            self.newTelem = False
            self.newEvent = False
        else:
            # Current = None
            # For now we're passing the empty value of the object, we might want to revise this in the future
            LOGGER.info("WARNING: No value received for: '{}' yet, sending empty object anyway".format(self.topic))
            Current = self.myData
        return Current

    def getCurrentTelemetry(self):
        return self.getCurrent()
    
    def getCurrentEvent(self):
        return self.getCurrent()

    def getCurrentCommand(self):
        return self.getCurrent()
    
    def waitEvent(self,tsleep=None,timeout=None):

        """ Loop for waiting for new event """
        if not tsleep:
            tsleep = self.tsleep
        if not timeout:
            timeout = self.timeout
            
        t0 =  time.time()
        while not self.newEvent:
            sys.stdout.flush()
            sys.stdout.write("Wating for %s event.. [%s]" % (self.topic, spinner.next()))
            sys.stdout.write('\r') 
            if time.time() - t0 > timeout:
                LOGGER.info("WARNING: Timeout reading for Event %s" % self.topic)
                self.newEvent = False
                break
            time.sleep(tsleep)
        return self.newEvent

    def resetEvent(self):
        ''' Simple function to set it back'''
        self.newEvent=False


class DDSSend(threading.Thread):
    

    def __init__(self, Device, sleeptime=1,timeout=5, threadID=1):


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
        ''' Function for threading'''
        self.waitForCompletion_Command()

    def get_mgr(self):
        # We get the equivalent of:
        #  mgr = SALPY_atHeaderService.SAL_atHeaderService()
        mgr = getattr(self.SALPY_lib,'SAL_{}'.format(self.Device))()
        return mgr

    def send_Command(self,cmd,**kwargs):
        ''' Send a Command to a Device'''
        timeout   = int(kwargs.pop('timeout',self.timeout))
        sleeptime = kwargs.pop('sleeptime',self.sleeptime)
        wait_command = kwargs.pop('wait_command',False)

        # Get the mgr handle
        mgr = self.get_mgr()
        mgr.salProcessor("{}_command_{}".format(self.Device,cmd))
        # Get the myData object
        myData = getattr(self.SALPY_lib,'{}_command_{}C'.format(self.Device,cmd))()
        LOGGER.info('Updating myData object with kwargs')
        myData = self.update_myData(myData,**kwargs)
        # Make it visible outside
        self.myData = myData
        self.cmd    = cmd
        self.timeout = timeout
        # For a Command we need the functions:
        # 1) issueCommand
        # 2) waitForCompletion -- this can be run separately
        self.issueCommand = getattr(mgr,'issueCommand_{}'.format(cmd))
        self.waitForCompletion = getattr(mgr,'waitForCompletion_{}'.format(cmd))
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
        #timeout = time.time() - self.cmdId_time - self.timeout
        LOGGER.info("Wait {} sec for Completion: {}".format(self.timeout,self.cmd)) 
        retval = self.waitForCompletion(self.cmdId,self.timeout)
        LOGGER.info("Done: {}".format(self.cmd)) 
        
    def ackCommand(self,cmd,cmdId):
        """ Just send the ACK for a command, it need the cmdId as input"""
        LOGGER.info("Sending ACK for Id: {} for Command: {}".format(cmdId,cmd))
        mgr = self.get_mgr()
        mgr.salProcessor("{}_command_{}".format(self.Device,cmd))
        ackCommand = getattr(mgr,'ackCommand_{}'.format(cmd))
        ackCommand(cmdId, SAL__CMD_COMPLETE, 0, "Done : OK");

    def acceptCommand(self,cmd):
        mgr = self.get_mgr()
        mgr.salProcessor("{}_command_{}".format(self.Device,cmd))
        acceptCommand = getattr(mgr,'acceptCommand_{}'.format(cmd))
        myData = getattr(self.SALPY_lib,'{}_command_{}C'.format(self.Device,cmd))()
        while True:
            cmdId = acceptCommand(myData)
            if cmdId > 0:
                time.sleep(1)
                break
        cmdId = acceptCommand(myData)            
        LOGGER.info("Accpeting cmdId: {} for Command: {}".format(cmdId,cmd))
        return cmdId
    
    def send_Event(self,event,**kwargs):
        ''' Send an Event from a Device'''

        sleeptime = kwargs.pop('sleep_time',self.sleeptime)
        priority  = kwargs.get('priority',1)

        myData = getattr(self.SALPY_lib,'{}_logevent_{}C'.format(self.Device,event))()
        LOGGER.info('Updating myData object with kwargs')
        myData = self.update_myData(myData,**kwargs)
        # Make it visible outside
        self.myData = myData
        # Get the logEvent object to send myData
        mgr = self.get_mgr()
        name = "{}_logevent_{}".format(self.Device,event)
        mgr.salEvent("{}_logevent_{}".format(self.Device,event))
        logEvent = getattr(mgr,'logEvent_{}'.format(event))
        LOGGER.info("Sending Event: {}".format(event)) 
        logEvent(myData, priority)
        LOGGER.info("Done: {}".format(event)) 
        time.sleep(sleeptime)

    def send_Telemetry(self,topic,**kwargs):
        ''' Send an Telemetry from a Device'''

        sleeptime = kwargs.pop('sleep_time',self.sleeptime)
        # Get the myData object
        myData = getattr(self.SALPY_lib,'{}_{}C'.format(self.Device,topic))()
        LOGGER.info('Updating myData object with kwargs')
        myData = self.update_myData(myData,**kwargs)
        # Make it visible outside
        self.myData = myData
        # Get the Telemetry object to send myData
        mgr = self.get_mgr()
        mgr.salTelemetryPub("{}_{}".format(self.Device,topic))
        putSample = getattr(mgr,'putSample_{}'.format(topic))
        LOGGER.info("Sending Telemetry: {}".format(topic)) 
        putSample(myData)
        LOGGER.info("Done: {}".format(topic)) 
        time.sleep(sleeptime)

    @staticmethod
    def update_myData(myData,**kwargs):
        """ Updating myData with kwargs """
        myData_keys = [a[0] for a in inspect.getmembers(myData) if not(a[0].startswith('__') and a[0].endswith('__'))]
        for key in kwargs:
            if key in myData_keys:
                setattr(myData,key,kwargs.get(key))
            else:
                LOGGER.info('key {} not in myData'.format(key))
        return myData

    def get_myData(self):
        """ Make a dictionary representation of the myData C objects"""
        myData_dic = {}
        myData_keys = [a[0] for a in inspect.getmembers(self.myData) if not(a[0].startswith('__') and a[0].endswith('__'))]
        for key in myData_keys:
            myData_dic[key] =  getattr(self.myData,key)
        return myData_dic
    
def command_sequencer(commands,Device='atHeaderService',wait_time=1, sleep_time=3):

    """
    Stand-alone function to send a sequence of OCS Commands
    """
    
    # We get the equivalent of:
    #  mgr = SALPY_atHeaderService.SAL_atHeaderService()
    # Load (if not in globals already) SALPY_{deviceName}
    SALPY_lib = load_SALPYlib(Device)

    mgr = getattr(SALPY_lib,'SAL_{}'.format(Device))()
    myData = {}
    issueCommand = {}
    waitForCompletion = {}
    for cmd in commands:
        myData[cmd] = getattr(SALPY_lib,'{}_command_{}C'.format(Device,cmd))()
        issueCommand[cmd] = getattr(mgr,'issueCommand_{}'.format(cmd))
        waitForCompletion[cmd] = getattr(mgr,'waitForCompletion_{}'.format(cmd))
        # If Start we send some non-sense value
        if cmd == 'Start':
            myData[cmd].configure = 'blah.json'
        
    for cmd in commands:
        LOGGER.info("Issuing command: {}".format(cmd)) 
        LOGGER.info("Wait for Completion: {}".format(cmd)) 
        cmdId = issueCommand[cmd](myData[cmd])
        waitForCompletion[cmd](cmdId,wait_time)
        LOGGER.info("Done: {}".format(cmd)) 
        time.sleep(sleep_time)

    return


    

