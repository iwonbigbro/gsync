#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Local version of the SyncFile type for handling local file access"""

import os, datetime
import libgsync.hashlib as hashlib
from libgsync.output import verbose, debug, itemize, Progress
from libgsync.drive.mimetypes import MimeTypes
from libgsync.sync import SyncType
from libgsync.sync.file import SyncFile, SyncFileInfo
from libgsync.options import GsyncOptions
from apiclient.http import MediaFileUpload, MediaUploadProgress


class SyncFileLocal(SyncFile):
    """SyncFileLocal class for representing local files"""

    def sync_type(self):
        return SyncType.LOCAL

    def get_uploader(self, path = None):
        info = self.get_info(path)
        if info is None: # pragma: no cover
            raise Exception("Could not obtain file information: %s" % path)

        path = self.get_path(path)

        # Test the file is readable.
        open(path, "r").close()

        return MediaFileUpload(
            path, mimetype = info.mimeType, resumable = True
        )

    def get_info(self, path = None):
        path = self.get_path(path)

        debug("Fetching local file metadata: %s" % repr(path))

        try:
            # Obtain the file info, following the link
            st_info = os.stat(path)
            filename = os.path.basename(path)

            if os.path.isdir(path):
                mimetype = MimeTypes.FOLDER
            else:
                mimetype = MimeTypes.get(path)

            md5_checksum = None
            if GsyncOptions.checksum:
                md5_checksum = self._md5_checksum(path)

            info = SyncFileInfo(
                title=filename,
                modifiedDate=datetime.datetime.utcfromtimestamp(
                    st_info.st_mtime
                ).isoformat(),
                mimeType=mimetype,
                description=st_info,
                fileSize=st_info.st_size,
                md5Checksum=md5_checksum,
                path=path
            )
            debug("Local file = %s" % repr(info), 3)
            debug("Local mtime: %s" % repr(info.modifiedDate))

        except OSError: # pragma: no cover
            debug("File not found: %s" % repr(path))
            return None

        debug("Local mtime: %s" % info.modifiedDate)

        return info


    def _update_dir(self, path, src):
        pass


    def _update_attrs(self, path, src, attrs):
        debug("Updating local file stats: %s" % repr(path))

        if GsyncOptions.dry_run:
            return

        if attrs.uid is not None:
            try:
                os.chown(path, attrs.uid, -1)
            except OSError: # pragma: no cover
                pass

        if attrs.gid is not None:
            try:
                os.chown(path, -1, attrs.gid)
            except OSError: # pragma: no cover
                pass

        if attrs.mode is not None:
            os.chmod(path, attrs.mode)

        if attrs.atime is None:
            attrs.atime = attrs.mtime

        if attrs.mtime is None:
            attrs.mtime = attrs.atime

        if attrs.mtime is not None:
            os.utime(path, (attrs.atime, attrs.mtime))


    def _md5_checksum(self, path):
        """Returns the checksum of the file"""

        if os.path.isdir(path):
            return None

        try:
            md5_gen = hashlib.new("md5")

            with open(path, "r") as fd:
                # Read the file in 1K chunks to avoid memory consumption
                while True:
                    chunk = fd.read(1024)
                    if not chunk:
                        break

                    md5_gen.update(chunk)

                return md5_gen.hexdigest()

        except Exception, ex: # pragma: no cover
            debug.exception(ex)

        return None


    def _create_dir(self, path, src=None):
        debug("Creating local directory: %s" % repr(path))

        if not GsyncOptions.dry_run:
            os.mkdir(path)


    def _create_file(self, path, src):
        path = self.get_path(path)

        debug("Creating local file: %s" % repr(path))

        fd = None
        try:
            if not GsyncOptions.dry_run:
                fd = open(path, "w")

        except Exception, ex: # pragma: no cover
            debug("Creation failed: %s" % repr(ex))

        finally:
            if fd is not None:
                fd.close()

    def _update_data(self, path, src):
        path = self.get_path(path)
        self.get_info(path)

        debug("Updating local file %s" % repr(path))

        uploader = src.get_uploader()

        fd = None
        bytes_written = 0
        chunk_size = uploader.chunksize()
        file_size = uploader.size()

        try:
            if not GsyncOptions.dry_run:
                fd = open(path, "w")

            progress = Progress(GsyncOptions.progress)

            while bytes_written < file_size:
                chunk = uploader.getbytes(bytes_written, chunk_size)

                debug("len(chunk) = %d" % len(chunk))

                if not chunk:
                    break

                if fd is not None:
                    fd.write(chunk)

                chunk_len = len(chunk)
                bytes_written += chunk_len
                self.bytes_written += chunk_len

                progress(MediaUploadProgress(bytes_written, file_size))

            debug("    Written %d bytes" % bytes_written)
            progress.complete(bytes_written)

            if bytes_written < file_size: # pragma: no cover
                raise Exception("Got %d bytes, expected %d bytes" % (
                    bytes_written, file_size
                ))

        except KeyboardInterrupt: # pragma: no cover
            debug("Interrupted")
            raise

        except Exception, ex: # pragma: no cover
            debug("Write failed: %s" % repr(ex))
            raise

        finally:
            if fd is not None:
                fd.close()

