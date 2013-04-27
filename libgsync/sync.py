# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, datetime, time, re
from libgsync.output import verbose, debug, itemize
from libgsync.drive import Drive, MimeTypes
from libgsync.options import Options

g_drive = None

class ESyncFileAbstractMethod(Exception):
    pass

class SyncFileInfo(object):
    id = None
    title = None
    modifiedDate = None
    mimeType = MimeTypes.NONE

    def __init__(self, id, title, modifiedDate, mimeType, **misc):
        self.id = id
        self.title = title
        self.modifiedDate = modifiedDate
        self.__modifiedDate = datetime.datetime.strptime(
            modifiedDate,
            "%a %b %d %H:%M:%S %Y"
        )
        self.mimeType = mimeType

    def __gt__(self, fileInfo):
        return bool(self.__modifiedDate > fileInfo.__modifiedDate)

    def __lt__(self, fileInfo):
        return bool(self.__modifiedDate < fileInfo.__modifiedDate)

    def __ge__(self, fileInfo):
        return bool(self.__modifiedDate >= fileInfo.__modifiedDate)

    def __le__(self, fileInfo):
        return bool(self.__modifiedDate <= fileInfo.__modifiedDate)

    def __eq__(self, fileInfo):
        return bool(self.__modifiedDate == fileInfo.__modifiedDate)

    def __ne__(self, fileInfo):
        return bool(self.__modifiedDate != fileInfo.__modifiedDate)


class SyncFileFactory(object):
    @staticmethod
    def create(path):
        path = re.sub(r'/+$', "", path)
        filepath = re.sub(r'^drive://+', "/", path)

        if path == filepath:
            debug("Creating SyncFileLocal(%s)" % filepath)
            return SyncFileLocal(filepath)

        debug("Creating SyncFileRemote(%s)" % filepath)
        return SyncFileRemote(filepath)

    
class SyncFile(object):
    path = None

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path

    def __add__(self, path):
        return os.path.join(self.path, path)

    def getInfo(self, path = None):
        raise ESyncFileAbstractMethod

    def _createDir(self, path):
        raise ESyncFileAbstractMethod

    def _createFile(self, path, src):
        raise ESyncFileAbstractMethod

    def _updateFile(self, path, src):
        raise ESyncFileAbstractMethod

    def _normaliseSource(self, src):
        srcInfo = None

        if src is not None:
            if not isinstance(src, SyncFile):
                src = SyncFileFactory.create(src)

            srcInfo = src.getInfo()

        return (src, srcInfo)

    def create(self, path, src = None):
        (src, srcInfo) = self._normaliseSource(src)

        if srcInfo is None or srcInfo.mimeType == MimeTypes.FOLDER:
            self._createDir(path)
            return

        self._createFile(path, src)

    def update(self, path, src):
        (src, srcInfo) = self._normaliseSource(src)

        if srcInfo is None or srcInfo.mimeType == MimeTypes.FOLDER:
            return

        self._updateFile(path, src)


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
                time.ctime(st_info.st_mtime),
                mimeType
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


class SyncFileRemote(SyncFile):
    def getInfo(self, path = None):
        global g_drive

        if path is None:
            path = self.path
        else:
            path = os.path.join(self.path, path)

        debug("Fetching remote file metadata: %s" % path)

        info = g_drive.stat(path)
        if info is None:
            debug("File not found: %s" % path)
            return None

        info = SyncFileInfo(**info)
        debug("Remote mtime: %s" % info.modifiedDate)

        return info

    def _createDir(self, path):
        debug("Creating remote directory: %s" % path)

    def _createFile(self, path, src):
        debug("Creating remote file: %s" % path)

    def _updateFile(self, path, src):
        debug("Updating remote file: %s" % path)


class Sync(Options):
    src = None
    dst = None

    def __init__(self, src, dst, options = None):
        global g_drive
        g_drive = Drive()
        self.initialiseOptions(options)

        self.src = SyncFileFactory.create(src)
        self.dst = SyncFileFactory.create(dst)

    def __call__(self, path):
        itemize_args = self._sync(path)

        if itemize_args is not None and self._opt_itemize_changes:
            itemize(*itemize_args)

    def _sync(self, path):
        debug("Synchronising: %s" % path)

        relPath = re.sub(r'^%s/' % str(self.src), "", path)
        debug("Destination: %s" % self.dst)
        debug("Relative: %s" % relPath)

        srcFile = self.src.getInfo(relPath)
        dstPath = self.dst + relPath
        dstFile = self.dst.getInfo(dstPath)
        create = False
        update = False
        folder = bool(srcFile.mimeType == MimeTypes.FOLDER)

        if dstFile is None or dstFile.mimeType != srcFile.mimeType:
            changes = bytearray(">++++++++++")
            create = True
        else:
            changes = bytearray("...........")

        if self._opt_times:
            if (not self._opt_update or folder) and srcFile != dstFile:
                changes[4] = 't'
                update = True
            else:
                debug("File up to date: %s" % path)
                return None
        elif not self._opt_update or srcFile > dstFile:
            if folder:
                debug("Don't update folders unless --times: %s" % path)
                return None

            changes[4] = 'T'
            update = True
        else:
            debug("File up to date: %s" % path)
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

        elif self._opt_ignore_existing:
            debug("File exists on the receiver, skipping: %s" % path)
            return None

        else:
            self.dst.update(dstPath, path)

        return (changes, relPath)
