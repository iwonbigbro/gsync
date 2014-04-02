#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Factory class for the SyncFile adapter"""

import os
from libgsync.output import debug
from libgsync.drive import Drive

class SyncFileFactory(object):
    """
    SyncFileFactory class creates either a remote or local SyncFile
    instance to be used with the SyncFile adapter.  Remote files are those
    that exist in the Google Drive space, while local files exist on the
    local system.  Both file classes share the same common interface.
    """

    @staticmethod
    @debug.function
    def create(path):
        """Creates a new SyncFile instance"""

        drive = Drive()

        if drive.is_drivepath(path):
            filepath = drive.normpath(path)

            from libgsync.sync.file.remote import SyncFileRemote
            return SyncFileRemote(filepath)

        else:
            filepath = os.path.normpath(path)

            from libgsync.sync.file.local import SyncFileLocal
            return SyncFileLocal(filepath)
