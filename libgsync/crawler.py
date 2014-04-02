# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""
Crawler module which provides the interface for crawling local and remote
file systems.
"""

import os, re, sys
from libgsync.sync import Sync
from libgsync.output import verbose, debug
from libgsync.options import GsyncOptions
from libgsync.drive import Drive
from libgsync.drive.mimetypes import MimeTypes
from libgsync.bind import bind


def os_walk_wrapper(path):
    """
    The os.walk function doesn't yield anything if passed a file.  This
    wrapper simply yields the file as if the directory had been provided
    as the path.
    """
    if os.path.isdir(path):
        for dirpath, dirs, files in os.walk(path):
            yield (dirpath, dirs, files)

    elif os.path.exists(path):
        dirpart, filepart = os.path.split(path)
        yield (dirpart, [], [filepart])


class Crawler(object):
    """
    Crawler class that defines an instance of a crawler that is bound to
    either a local or remote filesystem.
    """
    def __init__(self, src, dst):
        self._dev = None
        self._src = None
        self._dst = None
        self._sync = None
        
        force_dest_file = GsyncOptions.force_dest_file

        self._drive = Drive()

        if self._drive.is_drivepath(src):
            self._walk_callback = bind("walk", self._drive)
            self._src = self._drive.normpath(src)
            info = self._drive.stat(self._src)

            if info and info.mimeType != MimeTypes.FOLDER:
                debug("Source is not a directory, forcing dest file: %s" % (
                    repr(self._src)
                ))
                force_dest_file = True
        else:
            self._walk_callback = os_walk_wrapper
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
    

    def _dev_check(self, device_id, path):
        """
        Checks if the path provided resides on the device specified by the
        device ID provided.

        @param {int} device_id    The device ID.
        @param {String} path      Path to verify.

        @return {bool} True if the path resides on device with the
                       specified ID.
        """
        if device_id is not None:
            st_info = os.stat(path)
            if st_info.st_dev != device_id:
                debug("Not on same device: %s" % repr(path))
                return False

        return True


    def _walk(self, path, generator, device_id):
        """
        Walks the path provided, calling the generator function on the path,
        which yields the subdirectories and files.  It then iterates these
        lists and calls the sync method '_sync'.

        @param {String} path          Path to walk.
        @param {Function} generator   Generator function to call on path.
        @param {int} device_id        Device ID for the path, None if device
                                      cannot be determined.
        """
        for dirpath, _, files in generator(path):
            debug("Walking: %s" % repr(dirpath))

            if not self._dev_check(device_id, dirpath):
                debug("Not on same device: %s" % repr(dirpath))
                continue

            if not GsyncOptions.force_dest_file:
                if GsyncOptions.dirs or GsyncOptions.recursive:

                    # Sync the directory but not its contents
                    debug("Synchronising directory: %s" % repr(dirpath))
                    self._sync(dirpath)
                else:
                    sys.stdout.write("skipping directory %s\n" % dirpath)
                    break

            for filename in files:
                absfile = os.path.join(dirpath, filename)
                if not self._dev_check(device_id, absfile):
                    continue
                    
                debug("Synchronising file: %s" % repr(absfile))
                self._sync(absfile)

            if not GsyncOptions.recursive:
                break


    def run(self):
        """
        Worker method called synchronously or as part of an asynchronous
        thread or subprocess.
        """
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
            self._walk(srcpath, self._walk_callback, self._dev)

        except KeyboardInterrupt, ex:
            print("\nInterrupted")
            raise

        except Exception, ex:
            debug.exception(ex)
            print("Error: %s" % repr(ex))

        finally:
            verbose("sent %d bytes  received %d bytes  %.2f bytes/sec" % (
                self._sync.total_bytes_sent,
                self._sync.total_bytes_received,
                self._sync.rate()
            ))

