# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, datetime, time, dateutil.parser, re
from dateutil.tz import tzutc

# Provide support for Windows environments.
try: import posix as os_platform
except Exception: import nt as os_platform # pragma: no cover

from zlib import compress, decompress
from base64 import b64encode, b64decode

try: import cPickle as pickle
except Exception: import pickle # pragma: no cover

from libgsync.output import verbose, debug, itemize
from libgsync.drive.mimetypes import MimeTypes
from libgsync.options import GsyncOptions

class EUnknownSourceType(Exception): # pragma: no cover
    pass

class EInvalidStatInfoType(Exception): # pragma: no cover
    def __init__(self, stype):
        self.statInfoType = stype

    def __str__(self):
        return "Invalid stat info type: %s" % self.statInfoType


class SyncFileInfoDatetime(object):
    __epoch = dateutil.parser.parse(
        "Thu, 01 Jan 1970 00:00:00 +0000",
        ignoretz=True
    ).replace(tzinfo = tzutc())
    __d = None

    def __(self, d):
        if isinstance(d, SyncFileInfoDatetime):
            return d.__d
        else:
            return d

    def __init__(self, datestring):
        d = dateutil.parser.parse(datestring, ignoretz=True)
        self.__d = d.replace(tzinfo = tzutc())

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except Exception, ex:
            return getattr(self.__d, name)

    def __repr__(self): return "SyncFileInfoDatetime(%s)" % repr(self.__d)
    def __str__(self): return self.__d.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
    def __secs(self): return (self.__d - self.__epoch).total_seconds()
    def __int__(self): return int(self.__secs())
    def __long__(self): return long(self.__secs())
    def __float__(self): return float(self.__secs())
    def __sub__(self, d): return self.__d - self.__(d)
    def __cmp__(self, d): return int(self.__d) - self.__(d)
    def __lt__(self, d): return (self.__d < self.__(d))
    def __le__(self, d): return (self.__d <= self.__(d))
    def __eq__(self, d): return (self.__d == self.__(d))
    def __ne__(self, d): return (self.__d != self.__(d))
    def __gt__(self, d): return (self.__d > self.__(d))
    def __ge__(self, d): return (self.__d >= self.__(d))


class SyncFileInfo(object):
    _dict = None

    # Note: The description field is currently overloaded to also provide
    #       custom metadata tags that currently aren't facilitated by Google
    #       Drive.
    def __init__(self, id, title, modifiedDate, mimeType,
                 description = None, fileSize = 0, md5Checksum = "",
                 **misc):

        self._dict = {
            'id': id,
            'title': title,
            'modifiedDate': SyncFileInfoDatetime(modifiedDate),
            'mimeType': mimeType,
            'description': description,
            'statInfo': None,
            'fileSize': int(fileSize),
            'md5Checksum': md5Checksum,
            'path': misc['path']
        }

        self._setStatInfo(description)

    def iteritems(self): return self._dict.iteritems()
    def values(self): return self._dict.values()
    def keys(self): return self._dict.keys()
    def items(self): return self._dict.items()

    def __getattr__(self, name):
        return self._dict[name]

    def __setattr__(self, name, value):
        if name == "_dict":
            object.__setattr__(self, name, value)
            return

        if name in [ "description", "statInfo" ]:
            self._setStatInfo(value)
            return

        debug("Setting: %s = %s" % (repr(name), repr(value)))

        self._dict[name] = value

    def __getitem__(self, name):
        return self._dict[name]

    def __repr__(self): # pragma: no cover
        return "SyncFileInfo(%s)" % ", ".join([
            "%s = %s" % (repr(k), repr(v)) for k, v in self._dict.iteritems()
        ])

    def _setStatInfo(self, value):
        if value is None:
            value = (0,0,0,0,0,0,0,0,0,0)

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
            value = value.encode("utf8")

        if isinstance(value, str):
            # First decode using new base64 compressed method.
            try:
                self._dict['statInfo'] = \
                    pickle.loads(decompress(b64decode(value)))
                self._dict['description'] = value
                return
            except Exception, ex:
                debug("Base 64 decode failed: %s" % repr(ex))
                pass

            # That failed, try to decode using old hex encoding.
            try:
                self._dict['statInfo'] = pickle.loads(value.decode("hex"))
                self._dict['description'] = value
                return
            except Exception, ex:
                debug("Hex decode failed: %s" % repr(ex))
                pass

            debug("Failed to decode string: %s" % repr(value))
            return

        raise EInvalidStatInfoType(type(value))


class SyncFile(object):
    path = None
    bytesRead = 0
    bytesWritten = 0

    def __init__(self, path):
        if isinstance(path, SyncFile):
            self._path = path._path
        else:
            self._path = path

    def __str__(self):
        return self._path

    def __add__(self, path):
        return self.getPath(path)

    def getPath(self, path = None):
        if not path: return self._path

        debug("Joining: %s with %s" % (repr(self._path), repr(path)))
        return os.path.join(self._path, path)

    def getUploader(self, path = None): # pragma: no cover
        raise NotImplementedError

    def getInfo(self, path = None): # pragma: no cover
        raise NotImplementedError

    def _createDir(self, path, src = None): # pragma: no cover
        raise NotImplementedError

    def _update_dir(self, path, src): # pragma: no cover
        raise NotImplementedError

    def _createFile(self, path, src): # pragma: no cover
        raise NotImplementedError

    def _update_data(self, path, src): # pragma: no cover
        raise NotImplementedError

    def _update_attrs(self, path, src, mode, uid, gid, mtime, atime): # pragma: no cover
        raise NotImplementedError

    def __createFile(self, path, src = None):
        self._createFile(path, src)
        self._update_data(path, src)
        self.__update_attrs(path, src)

    def __createDir(self, path, src = None):
        self._createDir(path, src)
        self.__update_attrs(path, src)

    def __update_data(self, path, src):
        self._update_data(path, src)

    def __update_dir(self, path, src):
        self._update_dir(path, src)

    def __update_attrs(self, path, src):
        if src is None: return

        srcInfo = src.getInfo()
        srcStatInfo = srcInfo.statInfo

        mode, uid, gid, atime, mtime = None, None, None, None, None

        debug("Updating: %s" % repr(path))

        if srcStatInfo is not None:
            if GsyncOptions.perms:
                mode = srcStatInfo.st_mode
                if mode is not None:
                    debug(" * Updating with mode: %d" % mode)

            if GsyncOptions.owner:
                uid = srcStatInfo.st_uid
                if uid is not None:
                    debug(" * Updating with uid: %d" % uid)

            if GsyncOptions.group:
                gid = srcStatInfo.st_gid
                if gid is not None:
                    debug(" * Updating with gid: %d" % gid)

        if GsyncOptions.times:
            mtime = float(srcInfo.modifiedDate)
        else:
            mtime = float(time.time())

        if srcStatInfo is not None:
            atime = srcStatInfo.st_atime
        else:
            atime = mtime

        debug(" * Updating with mtime: %0.2f" % mtime)
        debug(" * Updating with atime: %0.2f" % atime)

        self._update_attrs(path, src, mode, uid, gid, mtime, atime)


    def _normaliseSource(self, src):
        srcPath, srcObj, srcInfo = None, None, None

        debug("src = %s" % repr(src), 3)
        debug("type(src) = %s" % type(src))

        if src is not None:
            from libgsync.sync.file.factory import SyncFileFactory

            if isinstance(src, SyncFileInfo):
                srcInfo = src
                srcObj = SyncFileFactory.create(srcInfo.path)
                srcPath = srcObj.path

            elif isinstance(src, SyncFile):
                srcObj = src
                srcInfo = src.getInfo()
                srcPath = src.path

            elif isinstance(src, str) or isinstance(src, unicode):
                srcPath = src
                srcObj = SyncFileFactory.create(srcPath)
                srcInfo = srcObj.getInfo()

            else:
                raise EUnknownSourceType("%s is a %s" % (
                    repr(src), type(src))
                )

        debug("srcInfo = %s" % repr(srcInfo), 3)

        return (srcPath, srcInfo, srcObj)

    def create(self, path, src = None):
        (srcPath, srcInfo, srcObj) = self._normaliseSource(src)

        if srcInfo is None or srcInfo.mimeType == MimeTypes.FOLDER:
            self.__createDir(path, srcObj)
            return

        self.__createFile(path, srcObj)

    def update_data(self, path, src):
        (srcPath, srcInfo, srcObj) = self._normaliseSource(src)

        if srcInfo is None or srcInfo.mimeType == MimeTypes.FOLDER:
            self.__update_dir(path, srcObj)
            return

        self.__update_data(path, srcObj)

    def update_attrs(self, path, src):
        (srcPath, srcInfo, srcObj) = self._normaliseSource(src)

        self.__update_attrs(path, srcObj)

    def normpath(self, path):
        return os.path.normpath(path)

    def relativeTo(self, relpath):
        path = self._path
        if path[-1] != "/": path += "/"

        expr = r'^%s+' % path
        relpath = self.normpath(relpath)

        debug("Creating relative path from %s and %s" % (
            repr(expr), repr(relpath)
        ))
        return os.path.normpath(re.sub(expr, "", relpath + "/"))

    def isremote(self):
        debug("self.__class__.__name__ == %s" % self.__class__.__name__)
        return (self.__class__.__name__ == "SyncFileRemote")

    def islocal(self):
        debug("self.__class__.__name__ == %s" % self.__class__.__name__)
        return (self.__class__.__name__ == "SyncFileLocal")
