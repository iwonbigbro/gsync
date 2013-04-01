# Copyright (C) 2013 Craig Phillips.  All rights reserved.

_verboseEnabled = False

def enable():
    global _verboseEnabled
    _verboseEnabled = True
    

def verbose(msg):
    global _verboseEnabled
    if _verboseEnabled:
        print(msg)
