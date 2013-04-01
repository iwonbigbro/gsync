# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, time, re
from libgsync.output import verbose, debug
from libgsync.drive import Drive, MimeTypes
from libgsync.options import Options

class Sync(Options):
    _remoteRoot = False
    _remoteDest = False

    def __init__(self, root, dest, options = None):
        self._drive = Drive()
        self._root = re.sub(r'/+$', "", root)

        self.initialiseOptions(options)

        if re.search(r'^drive://', root) is None:
            debug("Local root: %s" % root)
            self._root = root
        else:
            debug("Remote root: %s" % root)
            self._remoteRoot = True
            self._root = re.sub(r'^drive://+', "/", root)

        if re.search(r'^drive://', dest) is None:
            self._dest = dest
            debug("Local destination: %s" % self._dest)
        else:
            debug("Remote destination: %s" % dest)
            self._remoteDest = True
            self._dest = re.sub(r'^drive://+', "/", dest)


    def _getRemoteFile(self, path):
        debug("Fetching remote file metadata: %s" % path)

        remote = self._drive.find(path)
        if remote is None:
            debug("File not found: %s" % path)
        else:
            debug("Remote mtime: %s" % remote['modifiedDate'])

        return remote


    def _getLocalFile(self, path):
        local = None

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
                mimeType = None

            local = {
                'title': filename,
                'fileExtension': extension,
                'modifiedDate': time.ctime(st_info.st_mtime),
                'mimeType': mimeType
            }
            debug("Local mtime: %s" % local['modifiedDate'])
        except OSError, e:
            debug("File not found: %s" % path)
            pass

        return local


    def _getFile(self, path, remote):
        debug("_getFile(%s, %d)" % (path, remote))

        if remote:
            return self._getRemoteFile(path)

        return self._getLocalFile(path)
        

    def __call__(self, path):
        debug("Synchronising: %s" % path)

        if self._opt_relative:
            # Supports the foo/./bar notation in rsync.
            destPath = self._dest + re.sub(r'^.*/\./', "", path)
        else:
            destPath = self._dest + path[len(self._root):]

        source = self._getFile(path, self._remoteRoot)
        dest = self._getFile(destPath, self._remoteDest)

        if dest is not None and self._opt_ignoreExisting:
            debug("File exists on the receiver, skipping: %s" % path)
            return

        # TODO: Synchronise the files

