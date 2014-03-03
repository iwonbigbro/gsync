#!/usr/bin/env python

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Provides an Adapter for local and remote sync file types"""

import os, datetime, time, re
from libgsync.output import verbose, debug, itemize
from libgsync.drive.mimetypes import MimeTypes
from libgsync.options import GsyncOptions
from libgsync.sync.file.factory import SyncFileFactory


NOCHANGE = 0x0000
CREATE = 0x0001
UPDATE_DATA = 0x0002
UPDATE_ATTRS = 0x0004


class SyncRules(object):
    """Used as an intermediate object for calculating file differences"""

    def __init__(self, src_file, dst_file, is_local=False):
        self.src_file = src_file
        self.dst_file = dst_file
        self.is_local = is_local
        self.changes = bytearray("           ")
        self.action = NOCHANGE

        if GsyncOptions.force_dest_file:
            self.is_dir = False
        else:
            self.is_dir = bool(src_file.mimeType == MimeTypes.FOLDER)

    @debug.function
    def skip_non_existing(self):
        """Skip creating new files on receiver if they don't already exist"""

        if not (GsyncOptions.existing and GsyncOptions.ignore_non_existing):
            return False

        return bool(self.dst_file is None)

    @debug.function
    def skip_existing(self):
        """Skip updating files on receiver if they already exist"""

        if not GsyncOptions.ignore_existing:
            return False

        return bool(self.dst_file is not None)

    @debug.function
    def skip_mimetype(self):
        """Something not provided by rsync.  Skips files if their mimetype is
        the same.  Useful for determining when they are not the same.
        """

        return self.src_file.mimeType == self.dst_file.mimeType
    
    @debug.function
    def skip_quickcheck(self):
        """Skip files based on files that are the same size and mtime"""

        if GsyncOptions.checksum:
            return False

        if GsyncOptions.ignore_times:
            return False

        if not self.skip_mimetype():
            return False

        return bool(
            (GsyncOptions.size_only or self.skip_mtime()) and \
            self.skip_size()
        )

    @debug.function
    def skip_mtime(self):
        """Skip files that share the same modification time"""

        return self.src_file.modifiedDate == self.dst_file.modifiedDate

    @debug.function
    def skip_newer(self):
        """Skip files that are newer on the receiver"""

        if not GsyncOptions.update:
            return False

        return self.src_file.modifiedDate <= self.dst_file.modifiedDate

    @debug.function
    def skip_size(self):
        """Skip files that match in size"""

        if self.src_file.fileSize != self.dst_file.fileSize:
            self.changes[3] = 's'
            return False

        self.changes[3] = '.'
        return True

    @debug.function
    def skip_checksum(self):
        """Skip files based on checksum, not mod-time & size"""

        if not GsyncOptions.checksum:
            return False

        if self.src_file.md5Checksum != self.dst_file.md5Checksum:
            self.changes[2] = 'c'
            return False

        self.changes[2] = '.'
        return True

    @debug.function
    def skip_append(self):
        """Skip files if appending is not possible due to destination being
        of equal or longer in length.
        """

        if not GsyncOptions.append:
            return False

        return self.src_file.fileSize >= self.dst_file.fileSize

    @debug.function
    def skip_dirs(self):
        """Skip directories if user is using no-dirs or is not using one of
        recursive or dirs modes.
        """

        if not self.is_dir:
            return False

        if GsyncOptions.recursive:
            return False

        if GsyncOptions.no_dirs:
            return True

        if GsyncOptions.files_from or GsyncOptions.list_only:
            return False

        return GsyncOptions.dirs

    def _apply_skip_create(self):
        """Apply the skips that apply only to file creation"""

        if self.skip_non_existing():
            return True

        if self.skip_existing():
            return True

        if self.dst_file is None:
            self.changes = bytearray("cf+++++++++")
            self.action |= CREATE

            if self.is_dir:
                self.changes[1] = 'd'

            return True

        return False

    def _apply_update_attrs(self):
        """Apply update attribute changes"""

        # First check what file attributes we should update, if any.
        if not self.skip_mtime():
            self.action |= UPDATE_ATTRS

            if GsyncOptions.times:
                self.changes[4] = 't'
            else:
                self.changes[4] = 'T'

        src_st, dst_st = self.src_file.statInfo, self.dst_file.statInfo

        if src_st and dst_st:
            if GsyncOptions.perms and dst_st.st_mode != src_st.st_mode:
                self.action |= UPDATE_ATTRS
                self.changes[5] = 'p'

            if GsyncOptions.owner and dst_st.st_uid != src_st.st_uid:
                self.action |= UPDATE_ATTRS
                self.changes[6] = 'o'
            
            if GsyncOptions.group and dst_st.st_gid != src_st.st_gid:
                self.action |= UPDATE_ATTRS
                self.changes[7] = 'g'

            # Rsync also provides support for these:
            #     Check acl = self.changes[9] = 'a'
            #     Check extended attributes = self.changes[10] = 'x'

    def _apply_skip_update(self):
        """Apply skips that are only applicable to data updates"""

        if self.skip_newer() or self.skip_quickcheck():
            return True

        if self.skip_checksum() or self.skip_append():
            return True

        if self.skip_size() or self.skip_dirs():
            return True

        return False

    def apply(self):
        """Performs the appropriate comparison operations on the files to
        determine what action should be taken.  Returns a tuple containing
        the action bitmask and change byte array.

        @return ( {bitmask} action, {bytearray} changes )
        """

        self.action = NOCHANGE

        if not self._apply_skip_create():
            self.changes = bytearray("...........")

            self._apply_update_attrs()

            if not self._apply_skip_update():
                self.action |= UPDATE_DATA

        if self.action & ( CREATE | UPDATE_DATA ):
            if self.is_local:
                self.changes[0] = '>'
            else:
                self.changes[0] = '<'

        return self.action, self.changes


class Sync(object):
    """The GSync Synchronisation Adapter Class"""

    src = None
    dst = None
    total_bytes_sent = 0L
    total_bytes_received = 0L
    started = None

    def __init__(self, src, dst):
        self.started = time.time()
        self.src = SyncFileFactory.create(src)
        self.dst = SyncFileFactory.create(dst)

    def __call__(self, path):
        self._sync(path)

    def _sync(self, path):
        """Internal synchronisation method, accessible by calling the class
        instance and providing the path to the file to synchronise.

        @param {String} path   The path to the file to synchronise.
        """

        debug("Synchronising: %s" % repr(path))

        rel_path = self.src.relativeTo(path)
        debug("Destination: %s" % repr(self.dst))
        debug("Relative: %s" % repr(rel_path))

        src_file = self.src.getInfo(rel_path)
        if src_file is None:
            debug("File not found: %s" % repr(path))
            return None

        dst_path, dst_file = None, None

        debug("force_dest_file = %s" % GsyncOptions.force_dest_file)

        if GsyncOptions.force_dest_file:
            dst_file = self.dst.getInfo()
            dst_path = self.dst + ""
            rel_path = os.path.basename(dst_path)
        else:
            dst_path = self.dst + rel_path
            dst_file = self.dst.getInfo(rel_path)

        debug("src_file = %s" % repr(src_file), 3)
        debug("dst_file = %s" % repr(dst_file), 3)

        rules = SyncRules(src_file, dst_file, is_local=self.dst.islocal())
        action, changes = rules.apply()

        if not action & (CREATE | UPDATE_DATA | UPDATE_ATTRS):
            debug("File up to date: %s" % repr(dst_path))
            return None

        if rules.is_dir:
            rel_path += "/"

        if GsyncOptions.itemize_changes:
            itemize(changes, rel_path)
        else:
            verbose(rel_path)

        try:
            if action & CREATE:
                self.dst.create(dst_path, src_file)

            elif action & UPDATE_DATA:
                self.dst.update_data(dst_path, src_file)

            if action & UPDATE_ATTRS:
                self.dst.update_attrs(dst_path, src_file)

        finally:
            self.total_bytes_sent += self.dst.bytesWritten
            self.total_bytes_received += self.dst.bytesRead

    def rate(self):
        """Returns the data transfer rate of the synchronisation"""

        delta = float(time.time()) - float(self.started)
        total_bytes = float(self.total_bytes_sent) + \
            float(self.total_bytes_received)

        return float(total_bytes) / float(delta)
