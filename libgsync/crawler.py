# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re
from threading import Thread
from libgsync.drive import Drive, MimeTypes
from libgsync.output import verbose, debug
from libgsync.options import Options
from libgsync.bind import bind

class Crawler(Options, Thread):
    _dev = None
    _drive = None

    def __init__(self, path, callback, options):
        self._callback = callback

        self.initialiseOptions(options)

        if re.search(r'^drive://', path) is None:
            self._path = path
            st_info = os.stat(self._path)

            if self._opt_one_file_system:
                self._dev = st_info.st_dev
        else:
            self._drive = Drive()
            self._path = re.sub(r'^drive://+', "/", path)

        Thread.__init__(self, name = "Crawler: %s" % path)
    

    def _devCheck(self, dev, path):
        if dev is not None:
            st_info = os.stat(path)
            if st_info.st_dev != dev:
                debug("Not on same dev: %s" % path)
                return False

        return True


    def _walk(self, path, generator, dev):
        for d, dirs, files in generator(path):
            if self._opt_dirs:
                # Sync the directory but not its contents
                self._callback(d)

            for f in files:
                f = os.path.join(d, f)
                if not self._devCheck(dev, f):
                    continue
                    
                self._callback(f)

            # Do nothing with directories if we are not synchronising them
            if self._opt_dirs:
                for subd in dirs:
                    subd = os.path.join(d, subd)

                    # Sync the directory but not its contents
                    self._callback(subd)

                    if self._opt_recursive and not self._devCheck(dev, subd):
                        continue

            if not self._opt_recursive:
                break


    def run(self):
        path = self._path
        generator = None

        if self._drive is None:
            debug("Enumerating: %s" % path)
            self._walk(path, os.walk, self._dev)
        else:
            debug("Enumerating: drive://%s" % path)
            self._walk(path, bind("walk", self._drive), None)
