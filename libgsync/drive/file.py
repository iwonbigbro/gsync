#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2013 Craig Phillips.  All rights reserved.

"""Drive file objects"""

class DriveFile(dict):
    """
    Defines the DriveFile adapter that provides an interface to a
    drive file information dictionary.
    """
    __setattr__ = dict.__setitem__


    def __getattr__(self, key):
        return self.get(key)


    def __repr__(self):
        return "DriveFile(%s)" % self.items()
