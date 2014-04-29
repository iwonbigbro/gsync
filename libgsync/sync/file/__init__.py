#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""SyncFile adapter for defining the implementation and interface of SyncFile
types.  Obvious types are local (system) and remote (Google drive) files.
"""

import os, datetime, time, dateutil.parser, re
from dateutil.tz import tzutc

# Provide support for Windows environments.
try:
    import posix as os_platform
except ImportError: # pragma: no cover
    import nt as os_platform # pylint: disable-msg=F0401

from zlib import compress, decompress
from base64 import b64encode, b64decode

try:
    import cPickle as pickle
except ImportError: # pragma: no cover
    import pickle

from libgsync.output import verbose, debug, itemize
from libgsync.drive.mimetypes import MimeTypes
from libgsync.options import GsyncOptions


class EUnknownSourceType(Exception): # pragma: no cover
    """UnknownSourceType exception"""

    pass


class EInvalidStatInfoType(Exception): # pragma: no cover
    """InvalidStatInfoType exception"""

    def __init__(self, stype):
        super(EInvalidStatInfoType, self).__init__(
            "Invalid stat info type: %s" % stype
        )


class SyncFileInfoDatetime(object):
    """SyncFileInfoDatetime class provides a datetime interface to the file
    information modification time.
    """

    __epoch = dateutil.parser.parse(
        "Thu, 01 Jan 1970 00:00:00 +0000",
        ignoretz=True
    ).replace(tzinfo = tzutc())
    __value = None

    def get_value(self):
        """Returns the native value of the object"""

        return self.__value

    def __native(self, d_obj):
        if isinstance(d_obj, SyncFileInfoDatetime):
            return d_obj.get_value()
        else:
            return d_obj

    def __init__(self, datestring):
        d_obj = dateutil.parser.parse(datestring, ignoretz=True)
        self.__value = d_obj.replace(tzinfo = tzutc())

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except KeyError:
            return getattr(self.__value, name)

    def __repr__(self):
        return "SyncFileInfoDatetime(%s)" % repr(self.__value)

    def __str__(self):
        return self.__value.strftime("%Y-%m-%dT%H:%M:%S.%fd+00:00")

    def __secs(self):
        delta = (self.__value - self.__epoch)
        try:
            return delta.total_seconds()
        except AttributeError: # pragma: no cover
            return (
                delta.microseconds + (
                    delta.seconds + delta.days * 24 * 3600
                ) * 10**6
            ) / 10**6

    def __int__(self):
        return int(self.__secs())

    def __long__(self):
        return long(self.__secs())

    def __float__(self):
        return float(self.__secs())

    def __sub__(self, d_obj):
        return self.__value - self.__native(d_obj)

    def __cmp__(self, d_obj):
        return int(self.__value) - self.__native(d_obj)

    def __lt__(self, d_obj):
        return (self.__value < self.__native(d_obj))

    def __le__(self, d_obj):
        return (self.__value <= self.__native(d_obj))

    def __eq__(self, d_obj):
        return (self.__value == self.__native(d_obj))

    def __ne__(self, d_obj):
        return (self.__value != self.__native(d_obj))

    def __gt__(self, d_obj):
        return (self.__value > self.__native(d_obj))

    def __ge__(self, d_obj):
        return (self.__value >= self.__native(d_obj))


class SyncFileInfo(object):
    """SyncFileInfo class provides access to the file information, such as
    the title, modification time, mimetype etc.
    """

    _dict = None

    # Note: The description field is currently overloaded to also provide
    #       custom metadata tags that currently aren't facilitated by Google
    #       Drive.
    def __init__(self, **kwargs):
        description = kwargs.get('description', None)
        file_size = int(kwargs.get('fileSize', 0))
        md5_sum = kwargs.get('md5Checksum', "")

        self._dict = {
            'id': kwargs['id'],
            'title': kwargs['title'],
            'modifiedDate': SyncFileInfoDatetime(kwargs['modifiedDate']),
            'mimeType': kwargs['mimeType'],
            'description': description,
            'statInfo': None,
            'fileSize': file_size,
            'md5Checksum': md5_sum,
            'path': kwargs['path']
        }

        self.set_stat_info(description)

    def iteritems(self):
        """Interface method"""
        return self._dict.iteritems()

    def values(self):
        """Interface method"""
        return self._dict.values()

    def keys(self):
        """Interface method"""
        return self._dict.keys()

    def items(self):
        """Interface method"""
        return self._dict.items()

    def __getattr__(self, name):
        return self._dict[name]

    def __setattr__(self, name, value):
        if name == "_dict":
            object.__setattr__(self, name, value)
            return

        if name in [ "description", "statInfo" ]:
            self.set_stat_info(value)
            return

        debug("Setting: %s = %s" % (repr(name), repr(value)))

        self._dict[name] = value

    def __getitem__(self, name):
        return self._dict[name]

    def __len__(self):
        return len(self._dict)

    def __delitem__(self, name):
        raise AttributeError

    def __setitem__(self, name, value):
        raise AttributeError

    def __repr__(self): # pragma: no cover
        return "SyncFileInfo(%s)" % ", ".join([
            "%s = %s" % (repr(k), repr(v)) for k, v in self._dict.iteritems()
        ])

    def set_stat_info(self, value):
        """Sets the file stat information.  Takes multiple parameter types:

        @param {tuple|list|stat_result|unicode|str} value
        """
        if value is None:
            value = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        if isinstance(value, tuple) or isinstance(value, list):
            value = os_platform.stat_result(tuple(value))
            self._dict['statInfo'] = value
            self._dict['description'] = \
                b64encode(compress(pickle.dumps(value))) 

            return
            
        if isinstance(value, os_platform.stat_result):
            try:
                self._dict['description'] = \
                    b64encode(compress(pickle.dumps(value))) 
                self._dict['statInfo'] = value
            except pickle.PicklingError:
                pass

            return

        if isinstance(value, unicode):
            value = unicode(value).encode("utf8")

        if isinstance(value, str):
            # First decode using new base64 compressed method.
            try:
                self._dict['statInfo'] = \
                    pickle.loads(decompress(b64decode(value)))
                self._dict['description'] = value
                return
            except Exception, ex:
                debug("Base 64 decode failed: %s" % repr(ex))

            # That failed, try to decode using old hex encoding.
            try:
                dvalue = str(value).decode("hex")
                self._dict['statInfo'] = pickle.loads(dvalue)
                self._dict['description'] = value
                return
            except Exception, ex:
                debug("Hex decode failed: %s" % repr(ex))

            debug("Failed to decode string: %s" % repr(value))
            return

        raise EInvalidStatInfoType(type(value))


class SyncFileAttrs(object):
    """Class representing attributes for a SyncFile class"""

    def __init__(self):
        self.mode = None
        self.uid = None
        self.gid = None
        self.mtime = None
        self.atime = None

    def __setattr__(self, name, value):
        if value is not None:
            debug(" * Updating with %s: %d" % (name, value))

        super(SyncFileAttrs, self).__setattr__(name, value)


class SyncFile(object):
    """SyncFile abstract base class"""

    def __init__(self, path):
        if isinstance(path, SyncFile):
            self._path = path.get_path()
        else:
            self._path = path

        self.bytes_read = 0
        self.bytes_written = 0

    def __str__(self):
        return self._path

    def __add__(self, path):
        return self.get_path(path)

    def get_path(self, path = None):
        """Returns the path of the SyncFile instance, or the path joined
        with the path provided.

        @param {str} path (default: None)
        """
        if not path:
            return self._path

        debug("Joining: %s with %s" % (repr(self._path), repr(path)))
        return os.path.join(self._path, path)

    def get_uploader(self, path = None): # pragma: no cover
        """Returns the uploader (e.g. MediaUpload) for synchronisation.

        @param {str} path    Path to the file beneath this object
                             (default: None)
        """

        raise NotImplementedError

    def get_info(self, path = None): # pragma: no cover
        """Returns information about the file

        @param {str} path    Path to the file beneath this object
                             (default: None)
        """

        raise NotImplementedError

    def _create_dir(self, path, src = None): # pragma: no cover
        """Pure virtual function"""
        raise NotImplementedError

    def _update_dir(self, path, src): # pragma: no cover
        """Pure virtual function"""
        raise NotImplementedError

    def _create_file(self, path, src): # pragma: no cover
        """Pure virtual function"""
        raise NotImplementedError

    def _update_data(self, path, src): # pragma: no cover
        """Pure virtual function"""
        raise NotImplementedError

    def _update_attrs(self, path, src, attrs): # pragma: no cover
        """Pure virtual function"""
        raise NotImplementedError

    def __create_file(self, path, src = None):
        self._create_file(path, src)
        self._update_data(path, src)
        self.__update_attrs(path, src)

    def __create_dir(self, path, src = None):
        self._create_dir(path, src)
        self.__update_attrs(path, src)

    def __update_data(self, path, src):
        self._update_data(path, src)

    def __update_dir(self, path, src):
        self._update_dir(path, src)

    def __update_attrs(self, path, src):
        if src is None:
            return

        src_info = src.get_info()
        src_stat_info = src_info.statInfo

        attrs = SyncFileAttrs()

        debug("Updating: %s" % repr(path))

        if src_stat_info is not None:
            if GsyncOptions.perms:
                attrs.mode = src_stat_info.st_mode

            if GsyncOptions.owner:
                attrs.uid = src_stat_info.st_uid

            if GsyncOptions.group:
                attrs.gid = src_stat_info.st_gid

        if GsyncOptions.times:
            attrs.mtime = float(src_info.modifiedDate)
        else:
            attrs.mtime = float(time.time())

        if src_stat_info is not None:
            attrs.atime = src_stat_info.st_atime
        else:
            attrs.atime = attrs.mtime

        self._update_attrs(path, src, attrs)


    def _normalise_source(self, src):
        """Normalises the source parameter, which can be one of:

        @param {SyncFile|str|SyncFileInfo} src
        """
        src_path, src_obj, src_info = None, None, None

        debug("src = %s" % repr(src), 3)
        debug("type(src) = %s" % type(src))

        if src is not None:
            from libgsync.sync.file.factory import SyncFileFactory

            if isinstance(src, SyncFileInfo):
                src_info = src
                src_obj = SyncFileFactory.create(src_info.path)
                src_path = src_obj.get_path()

            elif isinstance(src, SyncFile):
                src_obj = src
                src_info = src.get_info()
                src_path = src.get_path()

            elif isinstance(src, str) or isinstance(src, unicode):
                src_path = src
                src_obj = SyncFileFactory.create(src_path)
                src_info = src_obj.get_info()

            else:
                raise EUnknownSourceType("%s is a %s" % (
                    repr(src), type(src))
                )

        debug("src_info = %s" % repr(src_info), 3)

        return (src_path, src_info, src_obj)

    def create(self, path, src = None):
        """Creates a file at the designated path"""

        _, src_info, src_obj = self._normalise_source(src)

        if src_info is None or src_info.mimeType == MimeTypes.FOLDER:
            self.__create_dir(path, src_obj)
            return

        self.__create_file(path, src_obj)

    def update_data(self, path, src):
        """Updates a file's data at the designated path"""

        _, src_info, src_obj = self._normalise_source(src)

        if src_info is None or src_info.mimeType == MimeTypes.FOLDER:
            self.__update_dir(path, src_obj)
            return

        self.__update_data(path, src_obj)

    def update_attrs(self, path, src):
        """Updates a file's attributes at the designated path"""

        _, _, src_obj = self._normalise_source(src)

        self.__update_attrs(path, src_obj)

    def normpath(self, path):
        """Virtual method providing subclasses the ability to override it"""

        return os.path.normpath(path)

    def relative_to(self, relpath):
        """Returns a path that is relative to this object"""

        path = self._path
        if path[-1] != "/":
            path += "/"

        expr = r'^%s+' % path
        relpath = self.normpath(relpath)

        debug("Creating relative path from %s and %s" % (
            repr(expr), repr(relpath)
        ))
        return os.path.normpath(re.sub(expr, "", relpath + "/"))

    def sync_type(self):
        """Pure virtual function"""

        raise NotImplementedError
