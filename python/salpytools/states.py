'''
Definitions for states of SAL compoments.
Taken from file toolsmod.py in:
https://github.com/lsst/ctrl_iip/blob/master/python/lsst/iip/toolsmod.py
'''

########
# Dictionary showing the state a transition ends in
next_state = {}
next_state["ENTER_CONTROL"] = "STANDBY"
next_state["EXIT_CONTROL"] = "OFFLINE"
next_state["START"] = "DISABLE"
next_state["ENABLE"] = "ENABLE"
next_state["DISABLE"] = "DISABLE"
next_state["STANDBY"] = "STANDBY"
next_state["SET_VALUE"] = "ENABLE"
next_state["ABORT"] = "DISABLE"
next_state["STOP"] = "DISABLE"
# Aliases
next_state["ENTERCONTROL"] = next_state["ENTER_CONTROL"] 
next_state["EXITCONTROL"] = next_state["EXIT_CONTROL"] 


summary_state_enum = {'DISABLE':0,
                      'ENABLE':1, 
                      'FAULT':2, 
                      'OFFLINE':3, 
                      'STANDBY':4}

state_enumeration = {}
state_enumeration["OFFLINE"] = 0
state_enumeration["STANDBY"] = 1
state_enumeration["DISABLE"] = 2
state_enumeration["ENABLE"] =  3
state_enumeration["FAULT"] =   4
state_enumeration["INITIAL"] = 5
state_enumeration["FINAL"] =   6

# This matrix expresses valid transitions and is reproduced in code afterwards.
#
#    \NEXT STATE
#STATE\
#      \ |Offline |Standby |Disabled|Enabled |Fault   |Initial |Final   |
#------------------------------------------------------------------------ 
#Offline | TRUE   | TRUE   |        |        |        |        |  TRUE  |
#------------------------------------------------------------------------
#Standby |  TRUE  | TRUE   |  TRUE  |        |  TRUE  |        |  TRUE  |
#------------------------------------------------------------------------
#Disable |        |  TRUE  |  TRUE  |  TRUE  |  TRUE  |        |        |
#------------------------------------------------------------------------
#Enable  |        |        |  TRUE  |  TRUE  |  TRUE  |        |        |
#------------------------------------------------------------------------
#Fault   |        |        |        |        |  TRUE  |        |        |
#------------------------------------------------------------------------
#Initial |        |  TRUE  |        |        |        | TRUE   |        |
#------------------------------------------------------------------------
#Final   |        |        |        |        |        |        | TRUE   |
#------------------------------------------------------------------------

w, h = 7, 7;
state_matrix = [[False for x in range(w)] for y in range(h)] 
state_matrix[0][6] = True
state_matrix[0][1] = True
state_matrix[1][6] = True
state_matrix[1][0] = True
state_matrix[1][2] = True
state_matrix[1][4] = True
state_matrix[2][1] = True
state_matrix[2][3] = True
state_matrix[2][4] = True
state_matrix[3][2] = True
state_matrix[3][4] = True
state_matrix[5][1] = True

# Set up same state transitions as allowed 
state_matrix[0][0] = True
state_matrix[1][1] = True
state_matrix[2][2] = True
state_matrix[3][3] = True
state_matrix[4][4] = True
state_matrix[5][5] = True
state_matrix[6][6] = True


