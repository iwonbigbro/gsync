# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import re
from libgsync.output import verbose, debug, itemize

class SyncFileFactory(object):
    @staticmethod
    def create(path):
        path = re.sub(r'/+$', "", path)
        filepath = re.sub(r'^drive://+', "/", path)

        if path == filepath:
            debug("Creating SyncFileLocal(%s)" % filepath)
            from libgsync.sync.file.local import SyncFileLocal
            return SyncFileLocal(filepath)

        debug("Creating SyncFileRemote(%s)" % filepath)
        from libgsync.sync.file.remote import SyncFileRemote
        return SyncFileRemote(filepath)
