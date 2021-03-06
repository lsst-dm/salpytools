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

'''
Definitions for states of SAL compoments.
Taken from file toolsmod.py in:
https://github.com/lsst/ctrl_iip/blob/master/python/lsst/iip/toolsmod.py
'''

########
# Dictionary showing the state a transition ends from command
# Note that ENABLE is the command and ENABLED is the resulting state
# Note that DISABLE is the command and DISABLED is the resulting state
next_state = {}
next_state["ENTER_CONTROL"] = "STANDBY"
next_state["EXIT_CONTROL"] = "OFFLINE"
next_state["START"] = "DISABLED"
next_state["ENABLE"] = "ENABLED"
next_state["DISABLE"] = "DISABLED"
next_state["STANDBY"] = "STANDBY"
next_state["SET_VALUE"] = "ENABLED"
next_state["ABORT"] = "DISABLED"
next_state["STOP"] = "DISABLED"
# Aliases
next_state["ENTERCONTROL"] = next_state["ENTER_CONTROL"]
next_state["EXITCONTROL"] = next_state["EXIT_CONTROL"]

state_names = ['DISABLED',
               'ENABLED',
               'FAULT',
               'OFFLINE',
               'STANDBY']


state_enumeration = {}
state_enumeration["OFFLINE"] = 0
state_enumeration["STANDBY"] = 1
state_enumeration["DISABLED"] = 2
state_enumeration["ENABLED"] = 3
state_enumeration["FAULT"] = 4
state_enumeration["INITIAL"] = 5
state_enumeration["FINAL"] = 6

# This matrix expresses valid transitions and is reproduced in code afterwards.
#
#     \NEXT STATE
# STATE\
#       \ |Offline |Standby |Disabled|Enabled |Fault   |Initial |Final   |
# ------------------------------------------------------------------------
# Offline |        | TRUE   |        |        |        |        |  TRUE  |
# ------------------------------------------------------------------------
# Standby |  TRUE  |        |  TRUE  |        |  TRUE  |        |  TRUE  |
# ------------------------------------------------------------------------
# Disable |        |  TRUE  |        |  TRUE  |  TRUE  |        |        |
# ------------------------------------------------------------------------
# Enable  |        |        |  TRUE  |        |  TRUE  |        |        |
# ------------------------------------------------------------------------
# Fault   |        |        |        |        |        |        |        |
# ------------------------------------------------------------------------
# Initial |        |  TRUE  |        |        |        |        |        |
# ------------------------------------------------------------------------
# Final   |        |        |        |        |        |        |        |
# ------------------------------------------------------------------------

w, h = 7, 7
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

# Disallow same state transitions
# state_matrix[0][0] = True
# state_matrix[1][1] = True
# state_matrix[2][2] = True
# state_matrix[3][3] = True
# state_matrix[4][4] = True
# state_matrix[5][5] = True
# state_matrix[6][6] = True
