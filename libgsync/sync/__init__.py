# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, datetime, time, re
from libgsync.output import verbose, debug, itemize
from libgsync.drive.mimetypes import MimeTypes
from libgsync.options import GsyncOptions
from libgsync.sync.file.factory import SyncFileFactory

class ESyncFileAbstractMethod(Exception):
    pass

class Sync(object):
    src = None
    dst = None
    totalBytesSent = 0L
    totalBytesReceived = 0L
    started = None

    def rate(self):
        delta = float(time.time() - self.started)
        totalBytes = float(self.totalBytesSent + self.totalBytesReceived)
        return float(totalBytes / delta)

    def __init__(self, src, dst):
        self.started = time.time()
        self.src = SyncFileFactory.create(src)
        self.dst = SyncFileFactory.create(dst)

    def __call__(self, path):
        changes = self._sync(path)

        if changes is not None:
            if GsyncOptions.itemize_changes:
                itemize(*changes)
            else:
                verbose(changes[1])
                
    def _sync(self, path):
        debug("Synchronising: %s" % path)

        relPath = self.src.relativeTo(path)
        debug("Destination: %s" % self.dst)
        debug("Relative: %s" % relPath)

        srcFile = self.src.getInfo(relPath)
        if srcFile is None:
            debug("File not found: %s" % path)
            return None

        dstPath = self.dst + relPath
        dstFile = self.dst.getInfo(relPath)
        create = False
        update = False
        folder = bool(srcFile.mimeType == MimeTypes.FOLDER)

        if dstFile is None or dstFile.mimeType != srcFile.mimeType:
            changes = bytearray(">++++++++++")
            create = True
        else:
            changes = bytearray("...........")

            if GsyncOptions.times:
                if (not GsyncOptions.update or folder) and srcFile != dstFile:
                    changes[4] = 't'
                    update = True
                else:
                    debug("File up to date: %s" % path)
                    return None

            if srcFile.fileSize != dstFile.fileSize:
                if folder:
                    debug("Folder size differs, so what...?: %s" % path)
                    return None

                debug("File size mismatch: %s" % path)
                debug("    source size:      %d" % srcFile.fileSize)
                debug("    destination size: %d" % dstFile.fileSize)
                if GsyncOptions.append:
                    update = True
                else:
                    create = True

            if (not GsyncOptions.update and (update or create)) or srcFile.modifiedDate > dstFile.modifiedDate:
                if folder:
                    debug("Don't update folders unless --times: %s" % path)
                    return None

                debug("File timestamp mismatch: %s" % path)
                debug("    source mtime:      %d" % srcFile.modifiedDate)
                debug("    destination mtime: %d" % dstFile.modifiedDate)
                changes[4] = 'T'
                update = True

            if not update and not create:
                debug("File up to date: %s" % dstPath)
                return None

        if folder:
            if create:
                changes[0] = 'c'

            changes[1] = 'd'
            relPath += "/"
        else:
            changes[1] = 'f'

            if update or create:
                changes[0] = '>'

        if create:
            self.dst.create(dstPath, path)

        elif GsyncOptions.ignore_existing:
            debug("File exists on the receiver, skipping: %s" % path)
            return None

        else:
            self.dst.update(dstPath, path)

        self.totalBytesSent += self.dst.bytesWritten
        self.totalBytesReceived += self.dst.bytesRead

        return (changes, relPath)
