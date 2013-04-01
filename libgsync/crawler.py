# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, threading, re
from libgsync.drive import Drive, MimeTypes
from libgsync.output import verbose, debug

class Crawler(threading.Thread):
    _dev = None
    _drive = None

    def __init__(self, path, callback, samedev = False):
        self._callback = callback

        if re.search(r'^drive://', path) is None:
            self._path = os.path.realpath(path)
            st_info = os.stat(self._path)

            if samedev:
                this._dev = st_info.st_dev
        else:
            self._drive = Drive()
            self._path = re.sub(r'^drive://+', "/", path)

        threading.Thread.__init__(self, name = "Crawler: %s" % path)


    def _remoteWalk(self, path):
        folders = []

        debug("Enumerating: drive://%s" % path)

        for dent in self._drive.list(str(path)):
            filename = dent['title']
            f = os.path.join(path, filename)

            if dent['mimeType'] == MimeTypes.FOLDER:
                folders.append(f)
            else:
                self._callback(f)

        for dent in folders:
            self._remoteWalk(f)


    def _localWalk(self, path):
        dev = self._dev

        debug("Enumerating: %s" % path)

        for d, dirs, files in os.walk(path):
            for f in files:
                f = os.path.join(d, f)

                if dev is not None:
                    st_info = os.stat(f)
                    if st_info.st_dev != dev:
                        debug("Not on same device, skipping: %s" % f)
                        continue
                    
                self._callback(f)

            for subd in dirs:
                subd = os.path.join(d, subd)

                if dev is not None:
                    st_info = os.stat(subd)
                    if st_info.st_dev != dev:
                        debug("Not on same device, skipping: %s" % subd)
                        continue

                self._localWalk(subd)


    def run(self):
        if self._drive is None:
            self._localWalk(self._path)
        else:
            self._remoteWalk(self._path)
