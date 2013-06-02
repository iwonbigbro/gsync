# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import re, os
from libgsync.output import debug
from libgsync.drive import Drive

class SyncFileFactory(object):
    @staticmethod
    def create(path):
        debug("SyncFileFactory.create(%s)" % path)

        drive = Drive()

        if drive.is_drivepath(path):
            filepath = drive.normpath(path)

            debug("Creating SyncFileRemote(%s)" % filepath)

            from libgsync.sync.file.remote import SyncFileRemote
            return SyncFileRemote(filepath)

        else:
            filepath = os.path.normpath(path)

            debug("Creating SyncFileLocal(%s)" % filepath)

            from libgsync.sync.file.local import SyncFileLocal
            return SyncFileLocal(filepath)
