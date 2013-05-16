# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re
from libgsync.output import verbose, debug, itemize
from libgsync.sync.file import SyncFile, SyncFileInfo

class SyncFileRemote(SyncFile):
    def stripped(self):
        return re.sub(r'^drive://+', "/", self.path)

    def getInfo(self, path = None):
        if path is None:
            path = self.path
        else:
            debug("Joining: %s with %s" % (self.path, path))
            path = os.path.join(self.path, path)
            debug("Got: %s" % path)

        debug("Fetching remote file metadata: %s" % path)

        # The Drive() instance is self caching.
        from libgsync.drive import Drive
        drive = Drive()

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
