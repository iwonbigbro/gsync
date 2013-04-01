# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, time, re
from libgsync.verbose import verbose
from libgsync.drive import Drive

class Sync():
    _remoteRoot = False
    _remoteDest = False

    def __init__(self, root, dest):
        self._drive = Drive()
        self._root = re.sub(r'/+$', "", root)

        if re.search(r'^drive://', root) is None:
            self._root = os.path.realpath(root)
        else:
            self._remoteRoot = True
            self._root = re.sub(r'^drive://+', "/", root)

        if re.search(r'^drive://', dest) is None:
            self._dest = os.path.realpath(dest)
        else:
            self._remoteDest = True
            self._dest = re.sub(r'^drive://+', "/", dest)


    def _getRemoteFile(self, path):
        verbose("Fetching remote file metadata: %s" % path)

        remote = self._drive.find(path)
        if remote is not None:
            verbose("Remote mtime: %s" % remote['modifiedDate'])

        return remote


    def _getLocalFile(self, path):
        local = None

        verbose("Fetching local file metadata: %s" % path)

        try:
            # Obtain the file info, following the link
            st_info = os.stat(os.path.realpath(path))

            root, extension = os.path.splitext(path)
            dirname, filename = os.path.split(root)

            local = {
                'title': filename,
                'fileExtension': extension,
                'modifiedDate': time.ctime(st_info.st_mtime)
            }
            verbose("Local mtime: %s" % local['modifiedDate'])
        except OSError, e:
            pass

        return local


    def _getFile(self, path, remote):
        if remote:
            return self._getRemoteFile(path)

        return self._getLocalFile(path)
        

    def __call__(self, path):
        verbose("Synchronising: %s" % path)

        source = self._getFile(
            os.path.join(self._root, path),
            self._remoteRoot
        )
        dest = self._getFile(
            os.path.join(self._dest, path),
            self._remoteDest
        )

        # TODO: Synchronise the files

