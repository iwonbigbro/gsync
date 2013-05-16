# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re, sys
from multiprocessing import Process
from libgsync.sync import Sync
from libgsync.output import verbose, debug
from libgsync.options import Options

class Crawler(Options, Process):
    _dev = None
    _drive = None
    _src = None
    _dst = None
    _options = None

    def __init__(self, src, dst, options):
        self._options = options
        self._dst = dst
        self._src = src

        self.initialiseOptions(options)

        if re.search(r'^drive://+', src) is None:
            st_info = os.stat(self._src)

            if self._opt_one_file_system:
                self._dev = st_info.st_dev
        else:
            from libgsync.drive import Drive
            self._drive = Drive()

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
                self._sync(d)
            else:
                sys.stdout.write("skipping directory %s\n" % d)
                break

            for f in files:
                f = os.path.join(d, f)
                if not self._devCheck(dev, f):
                    continue
                    
                debug("Synchronising file: %s" % f)
                self._sync(f)

            if not self._opt_recursive:
                break


    def run(self):
        srcpath = self._src
        generator = None
        prefix = ""

        srcpath = re.sub(r'^drive://+', "/", srcpath)
        if srcpath != self._src:
            prefix = "drive://"

        basepath, path = os.path.split(srcpath)
        basepath = prefix + basepath

        debug("Source prefix: %s" % prefix)
        debug("Source srcpath: %s" % srcpath)
        debug("Source basepath: %s" % basepath)
        debug("Source path: %s" % path)

        if self._opt_relative:
            # Supports the foo/./bar notation in rsync.
            path = re.sub(r'^.*/\./', "", path)

        self._sync = Sync(basepath, self._dst, self._options)

        debug("Enumerating: %s" % srcpath)

        if self._drive is None:
            self._walk(srcpath, os.walk, self._dev)
        else:
            from libgsync.bind import bind
            self._walk(srcpath, bind("walk", self._drive), None)

        verbose("sent %d bytes  received %d bytes  %.2f bytes/sec" % (
            self._sync.totalBytesSent,
            self._sync.totalBytesReceived,
            self._sync.rate()
        ))

