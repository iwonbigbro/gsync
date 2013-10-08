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
            if not GsyncOptions.itemize_changes:
                verbose(changes[1])
                
    def _sync(self, path):
        debug("Synchronising: %s" % repr(path))

        relPath = self.src.relativeTo(path)
        debug("Destination: %s" % repr(self.dst))
        debug("Relative: %s" % repr(relPath))

        srcFile = self.src.getInfo(relPath)
        if srcFile is None:
            debug("File not found: %s" % repr(path))
            return None

        debug("srcFile = %s" % repr(srcFile))

        folder = bool(srcFile.mimeType == MimeTypes.FOLDER)
        dstPath = None
        dstFile = None
        create = False
        update = False

        force_dest_file = GsyncOptions.force_dest_file
        debug("force_dest_file = %s" % force_dest_file)

        # If GsyncOptions.force_dest_file is None, the following are ignored.
        if force_dest_file:
            folder = False
            dstFile = self.dst.getInfo()
            dstPath = self.dst + ""
            relPath = os.path.basename(dstPath)
            debug("Forcing destination file: %s" % repr(dstPath))

        else:
            dstPath = self.dst + relPath
            dstFile = self.dst.getInfo(relPath)
            debug("Defaulting destination directory: %s" % repr(dstPath))

        if dstFile is None:
            debug("File not found: %s" % repr(dstPath))
        elif dstFile.mimeType != srcFile.mimeType:
            debug("Destination mimetype(%s) != source mimetype(%s)" % (
                dstFile.mimeType, srcFile.mimeType
            ))

        if dstFile is None or dstFile.mimeType != srcFile.mimeType:
            changes = bytearray("+++++++++++")
            create = True
        else:
            changes = bytearray("...........")

            if GsyncOptions.update:
                if srcFile.modifiedDate <= dstFile.modifiedDate:
                    debug("File up to date: %s" % repr(path))
                    return None

            if srcFile.fileSize != dstFile.fileSize:
                if folder:
                    debug("Folder size differs, so what...?: %s" % repr(path))
                    return None

                debug("File size mismatch: %s" % repr(path))
                debug("    source size:      %d" % srcFile.fileSize)
                debug("    destination size: %d" % dstFile.fileSize)

                if GsyncOptions.append:
                    update = True
                else:
                    create = True

                changes[3] = 's'

            if srcFile.modifiedDate >= dstFile.modifiedDate:
                if folder and not GsyncOptions.times:
                    debug("Don't update folders unless --times: %s" % 
                        repr(path))
                    return None

                debug("File timestamp mismatch: %s" % repr(path))
                debug("    source mtime:      %d" % int(srcFile.modifiedDate))
                debug("    destination mtime: %d" % int(dstFile.modifiedDate))
                
                if GsyncOptions.times:
                    changes[4] = 't'
                else:
                    changes[4] = 'T'

                update = (srcFile.modifiedDate > dstFile.modifiedDate)

            elif GsyncOptions.update:
                debug("Skipping, dest file is newer: %s" % repr(dstPath))
                return None

            if update or create:
                if srcFile.statInfo and dstFile.statInfo:
                    dstSt = dstFile.statInfo
                    srcSt = srcFile.statInfo

                    if GsyncOptions.perms and dstSt.st_mode != srcSt.st_mode:
                        changes[5] = 'p'

                    if GsyncOptions.owner and dstSt.st_uid != srcSt.st_uid:
                        changes[6] = 'o'
                    
                    if GsyncOptions.group and dstSt.st_gid != srcSt.st_gid:
                        changes[7] = 'g'

                if srcFile.modifiedTime != dstFile.modifiedTime:
                    if GsyncOptions.times:
                        changes[4] = 't'
                    else:
                        changes[4] = 'T'

            # TODO: Check acl = changes[9] = 'a'
            # TODO: Check extended attributes = changes[10] = 'x'

            if not update and not create:
                debug("File up to date: %s" % repr(dstPath))
                return None

        if folder:
            if create:
                changes[0] = 'c'

            changes[1] = 'd'
            relPath += "/"
        else:
            changes[1] = 'f'

            if update or create:
                if self.dst.islocal():
                    changes[0] = '>'
                else:
                    changes[0] = '<'

        if GsyncOptions.itemize_changes:
            itemize(changes, relPath)

        try:
            if create:
                self.dst.create(dstPath, srcFile)

            elif GsyncOptions.ignore_existing:
                debug("File exists on the receiver, skipping: %s" % (
                    repr(path)
                ))
                return None

            elif update:
                self.dst.update(dstPath, srcFile)

        except KeyboardInterrupt, e:
            debug("Interrupted")
            raise
        finally:
            self.totalBytesSent += self.dst.bytesWritten
            self.totalBytesReceived += self.dst.bytesRead

        return (changes, relPath)
