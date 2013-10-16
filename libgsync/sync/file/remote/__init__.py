# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re, datetime
from libgsync.output import verbose, debug, itemize, Progress
from libgsync.sync.file import SyncFile, SyncFileInfo
from libgsync.options import GsyncOptions
from apiclient.http import MediaIoBaseUpload, MediaUploadProgress
from libgsync.drive import Drive

class SyncFileRemote(SyncFile):
    def __init__(self, path):
        super(SyncFileRemote, self).__init__(path)
        self._path = self.normpath(path)

    def normpath(self, path):
        return Drive().normpath(path)

    def strippath(self, path):
        return Drive().strippath(path)

    def getPath(self, path = None):
        if path is None or path == "":
            return self._path

        selfStripPath = self.strippath(self._path)
        stripPath = self.strippath(path)

        debug("Joining: %s with %s" % (repr(selfStripPath), repr(stripPath)))
        ret = self.normpath(os.path.join(selfStripPath, stripPath))

        debug(" * got: %s" % repr(ret))
        return ret

    def getUploader(self, path = None):
        info = self.getInfo(path)
        if info is None:
            raise Exception("Could not obtain file information: %s" % path)

        path = self.getPath(path)
        drive = Drive()

        debug("Opening remote file for reading: %s" % repr(path))

        f = drive.open(path, "r")
        if f is None:
            raise Exception("Open failed: %s" % path)

        return MediaIoBaseUpload(f, info.mimeType, resumable=True)

    def getInfo(self, path = None):
        path = self.getPath(path)

        debug("Fetching remote file metadata: %s" % repr(path))

        # The Drive() instance is self caching.
        drive = Drive()

        info = drive.stat(path)
        if info is None:
            debug("File not found: %s" % repr(path))
            return None

        debug("Remote file metadata = %s" % repr(info))
        info = SyncFileInfo(**info)
        debug("Remote mtime: %s" % info.modifiedDate)

        return info

    def _createDir(self, path, src = None):
        debug("Creating remote directory: %s" % repr(path))

        if not GsyncOptions.dry_run:
            drive = Drive()
            drive.mkdir(path)

    def _createFile(self, path, src):
        debug("Creating remote file: %s" % repr(path))

        if GsyncOptions.dry_run: return

        drive = Drive()
        info = drive.create(path, src.getInfo())

        if info is None:
            debug("Creation failed")

    def _updateFile(self, path, src):
        debug("Updating remote file: %s" % repr(path))

        totalBytesWritten = self.bytesWritten
        bytesWritten = 0
        info = src.getInfo()

        def _callback(status):
            bytesWritten = int(status.resumable_progress)
            self.bytesWritten = totalBytesWritten + bytesWritten
            
        progress = Progress(GsyncOptions.progress, _callback)

        if GsyncOptions.dry_run:
            bytesWritten = info.fileSize
            progress(MediaUploadProgress(bytesWritten, bytesWritten))
        else:
            progress.bytesTotal = info.fileSize

            drive = Drive()
            info = drive.update(path, info, src.getUploader(), progress)

            if info is not None:
                bytesWritten = long(info.get('fileSize', '0'))
                debug("Final file size: %d" % bytesWritten)
            else:
                debug("Update failed")

        progress.complete(bytesWritten)
        self.bytesWritten = totalBytesWritten + bytesWritten

    def _updateStats(self, path, src, mode, uid, gid, mtime, atime):
        debug("Updating remote file stats: %s" % repr(path))

        if GsyncOptions.dry_run: return

        info = self.getInfo(path)
        if not info: return

        st_info = list(tuple(info.statInfo))

        if mode is not None:
            st_info[0] = mode
        if uid is not None:
            st_info[4] = uid
        if gid is not None:
            st_info[5] = gid
        if atime is not None:
            st_info[7] = atime
        
        info._setStatInfo(st_info)

        mtime_utc = datetime.datetime.utcfromtimestamp(mtime).isoformat()
            
        Drive().update(path, properties = {
            'description': info.description,
            'modifiedDate': mtime_utc,
        }, options = {
            'setModifiedDate': GsyncOptions.times
        })
