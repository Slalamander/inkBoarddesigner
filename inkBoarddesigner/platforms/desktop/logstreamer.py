"""Module for streaming logs on desktop

Spawns a new process which connects to a localhost socket to receive logs
"""

##This file (maybe, may just become its own function or smth) will:
## - Add a logstreamhandler to the log handlers with host localhost
## - call the inkBoard logs command in a subprocess which should open a new terminal window
## - await the process, which returns when the window is closed etc.
## clean up: close the logstreamer and remove it from the handler