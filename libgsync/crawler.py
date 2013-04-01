# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re
from threading import Thread
from libgsync.drive import Drive, MimeTypes
from libgsync.output import verbose, debug
from libgsync.options import Options

class Crawler(Options, Thread):
    _dev = None
    _drive = None

    def __init__(self, path, callback, options):
        self._callback = callback

        self.initialiseOptions(options)

        if re.search(r'^drive://', path) is None:
            self._path = path
            st_info = os.stat(self._path)

            if self._opt_samedev:
                self._dev = st_info.st_dev
        else:
            self._drive = Drive()
            self._path = re.sub(r'^drive://+', "/", path)

        Thread.__init__(self, name = "Crawler: %s" % path)


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

            # Do nothing with directories if we are not synchronising them
            if self._opt_recursive or self._opt_dirs:
                for dent in folders:
                    if self._opt_recursive:
                        # Sync the directory and contents
                        self._remoteWalk(f)
                    else:
                        # Sync the directory but not its contents
                        self._callback(f)


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

            # Do nothing with directories if we are not synchronising them
            if self._opt_recursive or self._opt_dirs:
                for subd in dirs:
                    subd = os.path.join(d, subd)

                    if self._opt_recursive:
                        # Sync the directory and contents
                        if dev is not None:
                            st_info = os.stat(subd)
                            if st_info.st_dev != dev:
                                debug("Not on same dev, skipping: %s" % subd)
                                continue

                        self._localWalk(subd)
                    else:
                        # Sync the directory but not its contents
                        self._callback(subd)


    def run(self):
        if self._drive is None:
            self._localWalk(self._path)
        else:
            self._remoteWalk(self._path)
