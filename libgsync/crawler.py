# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re, traceback, sys
#from threading import Thread
from multiprocessing import Process
from libgsync.sync import Sync
from libgsync.drive import Drive, MimeTypes
from libgsync.output import verbose, debug
from libgsync.options import Options
from libgsync.bind import bind

class Crawler(Options, Process):
    _dev = None
    _drive = None
    _src = None
    _dst = None
    _options = None

    def __init__(self, src, dst, options):
        self._options = options
        self._dst = dst

        self.initialiseOptions(options)

        if re.search(r'^drive://', src) is None:
            self._src = src
            st_info = os.stat(self._src)

            if self._opt_one_file_system:
                self._dev = st_info.st_dev
        else:
            self._drive = Drive()
            self._src = re.sub(r'^drive://+', "/", src)

        super(Crawler, self).__init__(name = "Crawler: %s" % src)
    

    def _devCheck(self, dev, path):
        if dev is not None:
            st_info = os.stat(path)
            if st_info.st_dev != dev:
                debug("Not on same dev: %s" % path)
                return False

        return True


    def _walk(self, path, generator, dev):
        for d, dirs, files in generator(path):
            debug("Walking: %s" % d)

            if not self._devCheck(dev, d):
                debug("Not on same device: %s" % d)
                continue

            if self._opt_dirs or self._opt_recursive:
                # Sync the directory but not its contents
                debug("Synchronising directory: %s" % d)
                self._callback(d)
            else:
                sys.stdout.write("skipping directory %s\n" % d)
                break

            for f in files:
                f = os.path.join(d, f)
                if not self._devCheck(dev, f):
                    continue
                    
                debug("Synchronising file: %s" % f)
                self._callback(f)

            if not self._opt_recursive:
                break


    def run(self):
        srcpath = self._src
        generator = None

        (basepath, path) = os.path.split(srcpath)

        if self._opt_relative:
            # Supports the foo/./bar notation in rsync.
            path = re.sub(r'^.*/\./', "", path)

        self._callback = Sync(basepath, self._dst, self._options)

        if self._drive is None:
            debug("Enumerating: %s" % srcpath)
            self._walk(srcpath, os.walk, self._dev)
        else:
            debug("Enumerating: drive://%s" % srcpath)
            self._walk(srcpath, bind("walk", self._drive), None)

