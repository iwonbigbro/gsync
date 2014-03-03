# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, datetime
from libgsync.output import verbose, debug, itemize, Progress
from libgsync.drive.mimetypes import MimeTypes
from libgsync.sync.file import SyncFile, SyncFileInfo
from libgsync.options import GsyncOptions
from apiclient.http import MediaFileUpload, MediaUploadProgress

class SyncFileLocal(SyncFile):
    def getUploader(self, path = None):
        info = self.getInfo(path)
        if info is None: # pragma: no cover
            raise Exception("Could not obtain file information: %s" % path)

        path = self.getPath(path)

        # Test the file is readable.
        open(path, "r").close()

        return MediaFileUpload(
            path, mimetype = info.mimeType, resumable = True
        )

    def getInfo(self, path = None):
        path = self.getPath(path)

        debug("Fetching local file metadata: %s" % repr(path))

        try:
            # Obtain the file info, following the link
            st_info = os.stat(path)
            dirname, filename = os.path.split(path)

            if os.path.isdir(path):
                mimeType = MimeTypes.FOLDER
            else:
                mimeType = MimeTypes.get(path)

            md5Checksum = None
            if GsyncOptions.checksum:
                md5Checksum = self._md5Checksum(path)

            info = SyncFileInfo(
                None,
                filename,
                datetime.datetime.utcfromtimestamp(
                    st_info.st_mtime
                ).isoformat(),
                mimeType,
                description = st_info,
                fileSize = st_info.st_size,
                md5Checksum = md5Checksum,
                path=path
            )
            debug("Local file = %s" % repr(info), 3)
            debug("Local mtime: %s" % repr(info.modifiedDate))
        except OSError, ex: # pragma: no cover
            debug("File not found: %s" % repr(path))
            return None

        debug("Local mtime: %s" % info.modifiedDate)

        return info

    def _update_attrs(self, path, src, mode, uid, gid, mtime, atime):
        debug("Updating local file stats: %s" % repr(path))

        if GsyncOptions.dry_run: return

        if uid is not None:
            try:
                os.chown(path, uid, -1)
            except OSError, ex: # pragma: no cover
                pass

        if gid is not None:
            try:
                os.chown(path, -1, gid)
            except OSError, ex: # pragma: no cover
                pass

        if mode is not None:
            os.chmod(path, mode)

        if atime is None: atime = mtime
        if mtime is None: mtime = atime
        if mtime is not None:
            os.utime(path, (atime, mtime))

    def _md5Checksum(self, path):
        if os.path.isdir(path):
            return None

        try:
            import hashlib
            m = hashlib.md5()

            with open(path, "r") as f:
                # Read the file in 1K chunks to avoid memory consumption
                while True:
                    chunk = f.read(1024)
                    if not chunk: break
                    m.update(chunk)

                return m.hexdigest()

        except Exception, ex: # pragma: no cover
            debug.exception(ex)

        return None

    def _createDir(self, path, src = None):
        debug("Creating local directory: %s" % repr(path))

        if not GsyncOptions.dry_run:
            os.mkdir(path)

    def _createFile(self, path, src):
        path = self.getPath(path)

        debug("Creating local file: %s" % repr(path))

        f = None
        try:
            if not GsyncOptions.dry_run:
                f = open(path, "w")
        except Exception, ex: # pragma: no cover
            debug("Creation failed: %s" % repr(ex))
        finally:
            if f is not None: f.close()

    def _update_data(self, path, src):
        path = self.getPath(path)
        info = self.getInfo(path)

        debug("Updating local file %s" % repr(path))

        uploader = src.getUploader()

        f = None
        bytesWritten = 0
        chunkSize = uploader.chunksize()
        fileSize = uploader.size()

        try:
            if not GsyncOptions.dry_run:
                f = open(path, "w")

            progress = Progress(GsyncOptions.progress)

            while bytesWritten < fileSize:
                chunk = uploader.getbytes(bytesWritten, chunkSize)

                debug("len(chunk) = %d" % len(chunk))

                if not chunk: break
                if f is not None: f.write(chunk)

                chunkLen = len(chunk)
                bytesWritten += chunkLen
                self.bytesWritten += chunkLen

                progress(MediaUploadProgress(bytesWritten, fileSize))

            debug("    Written %d bytes" % bytesWritten)
            progress.complete(bytesWritten)

            if bytesWritten < fileSize: # pragma: no cover
                raise Exception("Got %d bytes, expected %d bytes" % (
                    bytesWritten, fileSize
                ))

        except KeyboardInterrupt: # pragma: no cover
            debug("Interrupted")
            raise

        except Exception, ex: # pragma: no cover
            debug("Write failed: %s" % repr(ex))
            raise

        finally:
            if f is not None: f.close()
