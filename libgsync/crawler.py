# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, re, sys
from libgsync.sync import Sync
from libgsync.output import verbose, debug
from libgsync.options import GsyncOptions
from libgsync.drive import Drive
from libgsync.drive.mimetypes import MimeTypes
from libgsync.bind import bind

# os.walk doesn't yield anything if passed a file.  This wrapper simply
# yields the file as if the directory had been provided as the path.
def os_walk_wrapper(path):
    if os.path.isdir(path):
        for d, dirs, files in os.walk(path):
            yield (d, dirs, files)
    elif os.path.exists(path):
        d, f = os.path.split(path)
        yield (d, [], [f])

class Crawler(object):
    def __init__(self, src, dst):
        self._dev = None
        self._src = None
        self._dst = None
        
        force_dest_file = GsyncOptions.force_dest_file

        self._drive = Drive()

        if self._drive.is_drivepath(src):
            self._walkCallback = bind("walk", self._drive)
            self._src = self._drive.normpath(src)
            info = self._drive.stat(self._src)

            if info and info.mimeType != MimeTypes.FOLDER:
                debug("Source is not a directory, forcing dest file: %s" % (
                    repr(self._src)
                ))
                force_dest_file = True
        else:
            self._walkCallback = os_walk_wrapper
            self._src = os.path.normpath(src)
            st_info = os.stat(self._src)

            if os.path.isfile(self._src):
                debug("Source is not a directory, forcing dest file: %s" % (
                    repr(self._src)
                ))
                force_dest_file = True

            if GsyncOptions.one_file_system:
                self._dev = st_info.st_dev

        if self._drive.is_drivepath(dst):
            self._dst = self._drive.normpath(dst)
            info = self._drive.stat(self._dst)

            if info and info.mimeType == MimeTypes.FOLDER:
                debug("Dest is a directory, not forcing dest file: %s" % (
                    repr(self._dst)
                ))
                force_dest_file = False
        else:
            self._dst = os.path.normpath(dst)
            if os.path.isdir(self._dst):
                debug("Dest is a directory, not forcing dest file: %s" % (
                    repr(self._dst)
                ))
                force_dest_file = False

        if src[-1] == "/":
            self._src += "/"

        if dst[-1] == "/":
            self._dst += "/"
            debug("Dest has trailing slash, not forcing dest file: %s" % (
                self._dst
            ))
            force_dest_file = False

        # Only update if not already set.
        if GsyncOptions.force_dest_file is None:
            debug("force_dest_file = %s" % force_dest_file)
            GsyncOptions.force_dest_file = force_dest_file

        #super(Crawler, self).__init__(name = "Crawler: %s" % src)
    

    def _devCheck(self, dev, path):
        if dev is not None:
            st_info = os.stat(path)
            if st_info.st_dev != dev:
                debug("Not on same dev: %s" % repr(path))
                return False

        return True


    def _walk(self, path, generator, dev):
        for d, dirs, files in generator(path):
            debug("Walking: %s" % repr(d))

            if not self._devCheck(dev, d):
                debug("Not on same device: %s" % repr(d))
                continue

            if not GsyncOptions.force_dest_file:
                if GsyncOptions.dirs or GsyncOptions.recursive:

                    # Sync the directory but not its contents
                    debug("Synchronising directory: %s" % repr(d))
                    self._sync(d)
                else:
                    sys.stdout.write("skipping directory %s\n" % d)
                    break

            for f in files:
                f = os.path.join(d, f)
                if not self._devCheck(dev, f):
                    continue
                    
                debug("Synchronising file: %s" % repr(f))
                self._sync(f)

            if not GsyncOptions.recursive:
                break


    def run(self):
        srcpath = self._src
        basepath, path = os.path.split(srcpath)

        if self._drive.is_drivepath(self._src):
            basepath = self._drive.normpath(basepath)

        debug("Source srcpath: %s" % repr(srcpath))
        debug("Source basepath: %s" % repr(basepath))
        debug("Source path: %s" % repr(path))

        if GsyncOptions.relative:
            # Supports the foo/./bar notation in rsync.
            path = re.sub(r'^.*/\./', "", path)

        self._sync = Sync(basepath, self._dst)

        debug("Enumerating: %s" % repr(srcpath))

        try:
            self._walk(srcpath, self._walkCallback, self._dev)

        except KeyboardInterrupt, e:
            print("\nInterrupted")
            raise

        except Exception, e:
            debug.exception(e)
            print("Error: %s" % repr(e))

        finally:
            verbose("sent %d bytes  received %d bytes  %.2f bytes/sec" % (
                self._sync.totalBytesSent,
                self._sync.totalBytesReceived,
                self._sync.rate()
            ))

