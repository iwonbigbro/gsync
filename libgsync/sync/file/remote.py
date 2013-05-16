# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os
from libgsync.output import verbose, debug, itemize
from libgsync.sync.file import SyncFile, SyncFileInfo

g_drive = None

class SyncFileRemote(SyncFile):
    def getDrive(self):
        global g_drive
        if g_drive is None:
            from libgsync.drive import Drive
            g_drive = Drive()

        return g_drive

    def getInfo(self, path = None):
        if path is None:
            path = self.path
        else:
            path = os.path.join(self.path, path)

        debug("Fetching remote file metadata: %s" % path)

        drive = self.getDrive()
        info = drive.stat(path)
        if info is None:
            debug("File not found: %s" % path)
            return None

        debug("Remote file metadata = %s" % str(info))
        info = SyncFileInfo(**info)
        debug("Remote mtime: %s" % info.modifiedDate)

        return info

    def _createDir(self, path):
        debug("Creating remote directory: %s" % path)

    def _createFile(self, path, src):
        debug("Creating remote file: %s" % path)

    def _updateFile(self, path, src):
        debug("Updating remote file: %s" % path)
