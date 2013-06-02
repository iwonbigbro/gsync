# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re, sys
from threading import Thread
from libgsync.sync import Sync
from libgsync.output import verbose, debug
from libgsync.options import GsyncOptions
from libgsync.drive import Drive
from libgsync.bind import bind

class Crawler(Thread):
    def __init__(self, src, dst):
        self._dev = None
        self._src = None
        self._dst = None

        self._drive = Drive()

        if self._drive.is_drivepath(src):
            self._walkCallback = bind("walk", self._drive)
            self._src = self._drive.normpath(src)
        else:
            self._walkCallback = os.walk
            self._src = os.path.normpath(src)
            st_info = os.stat(self._src)

            if GsyncOptions.one_file_system:
                self._dev = st_info.st_dev

        if self._drive.is_drivepath(dst):
            self._dst = self._drive.normpath(dst)
        else:
            self._dst = os.path.normpath(dst)

        if src[-1] == "/": self._src += "/"
        if dst[-1] == "/": self._dst += "/"

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

            if GsyncOptions.dirs or GsyncOptions.recursive:
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

            if not GsyncOptions.recursive:
                break


    def run(self):
        srcpath = self._src
        basepath, path = os.path.split(srcpath)

        if self._drive.is_drivepath(self._src):
            basepath = self._drive.normpath(basepath)

        debug("Source srcpath: %s" % srcpath)
        debug("Source basepath: %s" % basepath)
        debug("Source path: %s" % path)

        if GsyncOptions.relative:
            # Supports the foo/./bar notation in rsync.
            path = re.sub(r'^.*/\./', "", path)

        self._sync = Sync(basepath, self._dst)

        debug("Enumerating: %s" % srcpath)

        try:
            self._walk(srcpath, self._walkCallback, self._dev)
        except KeyboardInterrupt:
            print("Terminating...")
            pass
        except Exception, e:
            debug.exception(e)
            print("Error: %s" % str(e))

        verbose("sent %d bytes  received %d bytes  %.2f bytes/sec" % (
            self._sync.totalBytesSent,
            self._sync.totalBytesReceived,
            self._sync.rate()
        ))

