# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, datetime
from libgsync.output import verbose, debug, itemize
from libgsync.drive.mimetypes import MimeTypes
from libgsync.sync.file import SyncFile, SyncFileInfo
from libgsync.options import GsyncOptions
from apiclient.http import MediaIoBaseUpload

class SyncFileLocal(SyncFile):
    def getUploader(self, path = None):
        info = self.getInfo(path)
        if info is None:
            raise Exception("Could not obtain file information: %s" % path)

        path = self.getPath(path)

        f = open(path, "r")
        if f is None:
            raise Exception("Open failed: %s" % path)

        return MediaIoBaseUpload(f, info.mimeType, resumable=True)

    def getInfo(self, path = None):
        path = self.getPath(path)

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
                description=st_info,
                fileSize=st_info.st_size,
                checksum="TODO:checksum",
                path=path
            )
        except OSError, e:
            debug("File not found: %s" % path)
            return None

        debug("Local mtime: %s" % info.modifiedDate)

        return info

    def _updateStats(self, path, src, mode, uid, gid, mtime, atime):
        if GsyncOptions.dry_run: return

        if uid is not None:
            try:
                os.chown(path, uid, -1)
            except OSError, e:
                pass

        if gid is not None:
            try:
                os.chown(path, -1, gid)
            except OSError, e:
                pass

        if mode is not None:
            os.chmod(path, mode)

        if atime is None: atime = mtime
        if mtime is None: mtime = atime
        if mtime is not None:
            os.utime(path, (atime, mtime))

    def _createDir(self, path, src = None):
        debug("Creating local directory: %s" % path)

        if not GsyncOptions.dry_run:
            os.mkdir(path)

    def _updateDir(self, path, src):
        debug("Updating local directory: %s" % path)

    def _createFile(self, path, src):
        path = self.getPath(path)

        debug("Creating local file: %s" % path)

        f = None
        try:
            if not GsyncOptions.dry_run:
                f = open(path, "w")
        except Exception, e:
            debug("Creation failed: %s" % str(e))
        finally:
            if f is not None: f.close()

    def _updateFile(self, path, src):
        path = self.getPath(path)
        info = self.getInfo(path)

        debug("Updating local file %s" % path)

        uploader = src.getUploader()

        f = None
        bytesWritten = 0
        chunkSize = uploader.chunksize()
        fileSize = uploader.size()

        try:
            if not GsyncOptions.dry_run:
                f = open(path, "w")

            while bytesWritten < fileSize:
                chunk = uploader.getbytes(bytesWritten, chunkSize)

                if not chunk: break
                if f is not None: f.write(chunk)

                bytesWritten += len(chunk)

            self.bytesWritten += bytesWritten
            debug("    Written %d bytes" % bytesWritten)

            if bytesWritten < fileSize:
                raise Exception("Got %d bytes, expected %d bytes" % (
                    bytesWritten, fileSize
                ))
        except Exception, e:
            debug("Write failed: %s" % str(e))
        finally:
            if f is not None: f.close()
