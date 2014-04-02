#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Remote file synchronisation"""

import os, re, datetime
from libgsync.output import verbose, debug, itemize, Progress
from libgsync.sync import SyncType
from libgsync.sync.file import SyncFile, SyncFileInfo
from libgsync.options import GsyncOptions
from apiclient.http import MediaIoBaseUpload, MediaUploadProgress
from libgsync.drive import Drive


class SyncFileRemote(SyncFile):
    """SyncFileRemote implementation for the SyncFile adapter"""
    
    def __init__(self, path):
        super(SyncFileRemote, self).__init__(path)
        self._path = self.normpath(path)

    def __repr__(self):
        return "SyncFileRemote(%s)" % repr(self._path)

    def sync_type(self):
        return SyncType.REMOTE

    def normpath(self, path):
        return Drive().normpath(path)

    def strippath(self, path):
        """Strips path of the 'drive://' prefix using the Drive() method"""

        return Drive().strippath(path)

    def get_path(self, path = None):
        if path is None or path == "":
            return self._path

        stripped_path = self.strippath(self._path)
        stripped_rel_path = self.strippath(path)

        debug("Joining: %s with %s" % (
            repr(stripped_path), repr(stripped_rel_path))
        )
        ret = self.normpath(os.path.join(stripped_path, stripped_rel_path))

        debug(" * got: %s" % repr(ret))
        return ret

    def get_uploader(self, path = None):
        info = self.get_info(path)
        if info is None:
            raise Exception("Could not obtain file information: %s" % path)

        path = self.get_path(path)
        drive = Drive()

        debug("Opening remote file for reading: %s" % repr(path))

        fd = drive.open(path, "r")
        if fd is None:
            raise Exception("Open failed: %s" % path)

        return MediaIoBaseUpload(fd, info.mimeType, resumable=True)

    def get_info(self, path = None):
        path = self.get_path(path)

        debug("Fetching remote file metadata: %s" % repr(path))

        # The Drive() instance is self caching.
        drive = Drive()

        info = drive.stat(path)
        if info is None:
            debug("File not found: %s" % repr(path))
            return None

        info = SyncFileInfo(**info)
        debug("Remote file = %s" % repr(info), 3)
        debug("Remote mtime: %s" % repr(info.modifiedDate))

        return info

    def _create_dir(self, path, src = None):
        debug("Creating remote directory: %s" % repr(path))

        if not GsyncOptions.dry_run:
            drive = Drive()
            drive.mkdir(path)

    def _create_file(self, path, src):
        debug("Creating remote file: %s" % repr(path))

        if GsyncOptions.dry_run:
            return

        drive = Drive()
        info = drive.create(path, src.get_info())

        if info is None:
            debug("Creation failed")

    def _update_dir(self, path, src):
        pass

    def _update_data(self, path, src):
        debug("Updating remote file: %s" % repr(path))

        total_bytes_written = self.bytes_written
        bytes_written = 0
        info = src.get_info()

        def __callback(status):
            bytes_written = int(status.resumable_progress)
            self.bytes_written = total_bytes_written + bytes_written
            
        progress = Progress(GsyncOptions.progress, __callback)

        if GsyncOptions.dry_run:
            bytes_written = info.fileSize
            progress(MediaUploadProgress(bytes_written, bytes_written))
        else:
            progress.bytesTotal = info.fileSize

            drive = Drive()
            info = drive.update(
                path, info, media_body=src.get_uploader(),
                progress_callback=progress
            )

            if info is not None:
                bytes_written = long(info.get('fileSize', '0'))
                debug("Final file size: %d" % bytes_written)
            else:
                debug("Update failed")

        progress.complete(bytes_written)
        self.bytes_written = total_bytes_written + bytes_written

    def _update_attrs(self, path, src, attrs):
        debug("Updating remote file attrs: %s" % repr(path))

        if GsyncOptions.dry_run:
            return

        info = self.get_info(path)
        if not info:
            return

        st_info = list(tuple(info.statInfo))

        if attrs.mode is not None:
            st_info[0] = attrs.mode
        if attrs.uid is not None:
            st_info[4] = attrs.uid
        if attrs.gid is not None:
            st_info[5] = attrs.gid
        if attrs.atime is not None:
            st_info[7] = attrs.atime
        
        info.set_stat_info(st_info)

        mtime_utc = datetime.datetime.utcfromtimestamp(
            attrs.mtime).isoformat()
            
        Drive().update(path, properties = {
            'description': info.description,
            'modifiedDate': mtime_utc,
        }, options = {
            'setModifiedDate': GsyncOptions.times
        })
