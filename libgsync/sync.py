# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, time, re
from libgsync.output import verbose, debug
from libgsync.drive import Drive

class Sync():
    _remoteRoot = False
    _remoteDest = False

    # Sync options
    _itemizeChanges = False
    _ignoreExisting = False

    def __init__(self, root, dest, options = None):
        self._drive = Drive()
        self._root = re.sub(r'/+$', "", root)

        self._initOptions(options)

        if re.search(r'^drive://', root) is None:
            debug("Local root: %s" % root)
            self._root = os.path.realpath(root)
        else:
            debug("Remote root: %s" % root)
            self._remoteRoot = True
            self._root = re.sub(r'^drive://+', "/", root)

        if re.search(r'^drive://', dest) is None:
            self._dest = os.path.realpath(dest)
            debug("Local destination: %s" % self._dest)
        else:
            debug("Remote destination: %s" % dest)
            self._remoteDest = True
            self._dest = re.sub(r'^drive://+', "/", dest)


    def _initOptions(self, options):
        if options is not None:
            for k, v in options.iteritems():
                if v == False: continue

                if k == '--itemize-changes':
                    self._itemizeChanges = True
                elif k == '--ignore-existing':
                    self._ignoreExisting = True


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
            st_info = os.stat(os.path.realpath(path))

            root, extension = os.path.splitext(path)
            dirname, filename = os.path.split(root)

            local = {
                'title': filename,
                'fileExtension': extension,
                'modifiedDate': time.ctime(st_info.st_mtime)
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

        source = self._getFile(path, self._remoteRoot)
        destPath = self._dest + path[len(self._root):]
        dest = self._getFile(destPath, self._remoteDest)

        if dest is not None and self._ignoreExisting:
            debug("File exists on the receiver, skipping: %s" % path)
            return

        # TODO: Synchronise the files

