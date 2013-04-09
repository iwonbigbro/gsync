# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, time, re
from libgsync.output import verbose, debug
from libgsync.drive import Drive, MimeTypes
from libgsync.options import Options

g_drive = None

class ESyncFileAbstractMethod(Exception):
    pass

class SyncFileInfo(object):
    title = None
    fileExtension = None
    modifiedDate = None
    mimeType = MimeTypes.NONE

    def __init__(self, title, fileExtension, modifiedDate, mimeType, **misc):
        self.title = title
        self.fileExtension = fileExtension
        self.modifiedDate = modifiedDate
        self.mimeType = mimeType

    
class SyncFile(object):
    path = None

    @staticmethod
    def create(path):
        path = re.sub(r'/+$', "", path)
        filepath = re.sub(r'^drive://+', "/", path)

        if path == filepath:
            debug("Creating SyncFileLocal(%s)" % filepath)
            return SyncFileLocal(filepath)

        debug("Creating SyncFileRemote(%s)" % filepath)
        return SyncFileRemote(filepath)

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path

    def __add__(self, path):
        return self.path + path

    def getInfo(self, path):
        raise ESyncFileAbstractMethod

    def createDir(self, path):
        raise ESyncFileAbstractMethod

    def openFile(self, path):
        raise ESyncFileAbstractMethod


class SyncFileLocal(SyncFile):

    def getInfo(self, path):
        debug("Fetching local file metadata: %s" % path)

        try:
            # Obtain the file info, following the link
            realpath = os.path.realpath(path)
            st_info = os.stat(realpath)
            root, extension = os.path.splitext(path)
            dirname, filename = os.path.split(root)

            if os.path.isdir(realpath):
                mimeType = MimeTypes.FOLDER
            else:
                mimeType = MimeTypes.NONE

            info = SyncFileInfo(
                filename,
                extension,
                time.ctime(st_info.st_mtime),
                mimeType
            )
        except OSError, e:
            debug("File not found: %s" % path)
            return None

        debug("Local mtime: %s" % info.modifiedDate)

        return info

    def createDir(self, path):
        debug("Creating local directory: %s" % path)
        pass

    def openFile(self, path, create = False):
        if create:
            debug("Creating local file: %s" % path)
            return None

        debug("Opening local file: %s" % path)
        return None


class SyncFileRemote(SyncFile):

    def getInfo(self, path):
        global g_drive

        debug("Fetching remote file metadata: %s" % path)

        info = g_drive.find(path)
        if info is None:
            debug("File not found: %s" % path)
            return None

        info = SyncFileInfo(**info)
        debug("Remote mtime: %s" % info.modifiedDate)

        return info

    def createDir(self, path):
        debug("Creating remote directory: %s" % path)
        pass

    def openFile(self, path, create = False):
        if create:
            debug("Creating remote file: %s" % path)
            return None

        debug("Opening remote file: %s" % path)
        return None


class Sync(Options):
    src = None
    dst = None

    def __init__(self, src, dst, options = None):
        global g_drive
        g_drive = Drive()
        self.initialiseOptions(options)

        self.src = SyncFile.create(src)
        self.dst = SyncFile.create(dst)

    def __call__(self, path):
        itemized, dst = self._sync(path)
        if self._opt_itemizeChanges:
            verbose('%s %s' % (str(itemized), dst))

    def _sync(self, path):
        debug("Synchronising: %s" % path)

        if self._opt_relative:
            # Supports the foo/./bar notation in rsync.
            dstPath = self.dst + re.sub(r'^.*/\./', "", path)
        else:
            dstPath = self.dst + path[len(str(self.src)):]

        srcFile = self.src.getInfo(path)
        dstFile = self.dst.getInfo(dstPath)

        if dstFile is None:
            itemized = bytearray("c++++++++++")
        else:
            itemized = bytearray("...........")

        if srcFile.mimeType == MimeTypes.FOLDER:
            itemized[1] = 'd'
        else:
            itemized[1] = 'f'

        if dstFile is not None and self._opt_ignoreExisting:
            debug("File exists on the receiver, skipping: %s" % path)
            return (itemized, dstPath)

        # A directory will have a trailing /.  Create directories and return.
        if srcFile.mimeType == MimeTypes.FOLDER:
            if dstFile is None:
                self.dst.createDir(dstPath)
            return (itemized, dstPath)

        # TODO: This needs some work.  When opening a file, we should check
        # modified date / checksum to see what file is newer and if they
        # differ and need synchronising.

        # Create file if it doesn't exist.
        if dstFile is None:
            create = True
        else:
            create = False

        f = self.dst.openFile(dstPath, create = create)

        # TODO: Synchronise the file contents.
        return (itemized, dstPath)
