# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, datetime
from libgsync.output import verbose, debug, itemize
from libgsync.drive.mimetypes import MimeTypes
from libgsync.sync.file import SyncFile, SyncFileInfo

class SyncFileLocal(SyncFile):
    def getInfo(self, path = None):
        if path is None:
            path = self.path
        else:
            debug("Joining: %s with %s" % (self.path, path))
            path = os.path.join(self.path, path)
            debug("Got: %s" % path)

        debug("Fetching local file metadata: %s" % path)

        try:
            # Obtain the file info, following the link
            st_info = os.stat(path)
            dirname, filename = os.path.split(path)

            if os.path.isdir(path):
                mimeType = MimeTypes.FOLDER
            else:
                mimeType = MimeTypes.NONE

            info = SyncFileInfo(
                None,
                filename,
                datetime.datetime.utcfromtimestamp(
                    st_info.st_mtime
                ).isoformat(),
                mimeType,
                st_info
            )
        except OSError, e:
            debug("File not found: %s" % path)
            return None

        debug("Local mtime: %s" % info.modifiedDate)

        return info

    def _createDir(self, path):
        debug("Creating local directory: %s" % path)


    def _createFile(self, path, src):
        debug("Creating local file: %s" % path)

    def _updateFile(self, path, src):
        debug("Updating local file: %s" % path)
