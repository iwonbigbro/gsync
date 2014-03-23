#!/usr/bin/env python

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""
Defines the MimeTypes static class used for mimetype related file
operations and for defining simple Google Drive types.
"""

from __future__ import absolute_import

class MimeTypes(object):
    """The MimeTypes static API class"""

    NONE = "none/unknown-mimetype"
    FOLDER = "application/vnd.google-apps.folder"
    BINARY_FILE = "application/octet-stream"

    @staticmethod
    def get(path):
        """
        Returns the mimetype of a file based on magic if the magic library
        is installed, otherwise uses the file extension method.
        """
        mimetype = None
        try:
            import magic
            mimetype = magic.from_file(path, mime=True)
        except Exception:
            import mimetypes
            mimetype = mimetypes.guess_type(path)[0]

        if mimetype is not None:
            return mimetype

        return MimeTypes.NONE
