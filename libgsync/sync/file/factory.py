# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import re
from libgsync.output import verbose, debug, itemize

class SyncFileFactory(object):
    @staticmethod
    def create(path):
        debug("SyncFileFactory.create(%s)" % path)

        if re.search(r'^drive://+', path) is None:
            filepath = re.sub(r'/+$', "", path)

            debug("Creating SyncFileLocal(%s)" % filepath)

            from libgsync.sync.file.local import SyncFileLocal
            return SyncFileLocal(filepath)

        else:
            filepath = re.sub(r'drive://+', "/", path)
            filepath = re.sub(r'([^/])/+$', "$1", filepath)

            debug("Creating SyncFileRemote(%s)" % filepath)

            from libgsync.sync.file.remote import SyncFileRemote
            return SyncFileRemote(filepath)
