#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""The GSync Drive module that provides an interface to the Google Drive"""

import os, sys, re, datetime, shelve, time

from contextlib import contextmanager

try:
    import simplejson as json
except ImportError:
    import json # pragma: no cover

import oauth2client.util
oauth2client.util.positional_parameters_enforcement = \
    oauth2client.util.POSITIONAL_IGNORE

from oauth2client.client import OAuth2Credentials
from apiclient.http import MediaUploadProgress
from libgsync.output import verbose, debug
from libgsync.drive.mimetypes import MimeTypes
from libgsync.drive.file import DriveFile

if debug.enabled(): # pragma: no cover
    import logging
    logging.getLogger().setLevel(logging.DEBUG)


class NoTTYError(Exception): # pragma: no cover
    """Raised for non-tty based terminal exceptions"""
    pass

class ExchangeError(Exception): # pragma: no cover
    """Step2_Exchange based exception type"""
    pass

class FileNotFoundError(Exception): # pragma: no cover
    """Raised when expected files/directories are not found"""
    def __init__(self, filename):
        super(FileNotFoundError, self).__init__(
            "File not found: %s" % repr(filename))

        self.filename = filename

class NoServiceError(Exception):
    """Raised when a service could not be obtained from apiclient"""
    pass


class DriveFileObject(object):
    """
    Defines an IO stream wrapper interface to a DriveFile.
    """
    def __init__(self, path, mode = "r"):
        # Public
        self.closed = False
        self.description = ""
        self.modified_date = datetime.datetime.now().isoformat()

        # Private
        drive = Drive()
        path = drive.normpath(path)

        self._path = path
        self._info = drive.stat(path)
        self._offset = 0
        self._size = 0
        self._mode = mode
        self._mimetype = MimeTypes.BINARY_FILE
        self._parent_id = None

        # Only mode support at present
        if mode != "r":
            raise IOError("Unsupported mode: %s" % mode)

        if self._info:
            # File size is set to None for empty documents.
            if self._info.fileSize is not None:
                self._size = int(self._info.fileSize)

            if self._info.mimeType is not None:
                self._mimetype = self._info.mimeType

            self.description = self._info.description

        self._dirname, self._filename = os.path.split(path)

    def __repr__(self): # pragma: no cover
        return "%s(%s, %s)" % (
            self.__class__.__name__, repr(self._path), repr(self._mode)
        )

    def _required_open(self):
        """Raises an exception when the file is not open"""
        if self.closed:
            raise IOError("File is closed: %s" % self._path)

    def _required_modes(self, modes):
        """
        Raises an exception when the current IO mode is not in the list
        of required modes.
        """
        if self._mode not in modes:
            import inspect
            curframe = inspect.currentframe()
            calframe = inspect.getouterframes(curframe, 2)
            name = calframe[1][3]
            raise IOError("Operation not permitted: %s()" % name)

    def revisions(self):
        """
        Obtains a list of file revisions for the file object.
        """
        with Drive().service() as service:
            revisions = service.revisions().list(
                fileId=self._info.id
            ).execute()

            return revisions.get('items', [])

        return None

    def mimetype(self, mimetype=None):
        """
        Returns the current file mimetype.
        """
        if mimetype is not None:
            self._mimetype = mimetype
        return self._mimetype

    def close(self):
        """Marks the file as closed to prevent further IO operations"""
        self.closed = True

    def flush(self): # pragma: no cover
        """Provides file interface method, but does nothing"""
        pass

    def seek(self, offset, whence = 0):
        """Sets the current file IO offset"""
        self._required_open()

        if whence == 0:
            self._offset = offset
        elif whence == 1:
            self._offset += offset
        elif whence == 2:
            self._offset = self._size - offset

    def tell(self):
        """Returns the current IO offset"""
        self._required_open()

        return self._offset

    # A pseudo function really, has no effect if no data is written after
    # calling this method.
    def truncate(self, size = None): # pragma: no cover
        """
        Truncates the file by locally setting its size to zero, but has
        no effect on the server side copy until the file is written to.
        """
        self._required_open()

        if size is None:
            size = self._offset
        self._size = size

    def read(self, length=None):
        """Reads 'length' bytes from the current offset"""
        if self._info is None:
            return ""

        self._required_open()

        with Drive().service() as service:
            http = service._http # pylint: disable-msg=W0212
            http.follow_redirects = False 

            if length is None:
                length = self._size - self._offset

            if length <= 0:
                return ""

            url = service.files().get(
                fileId=self._info.id
            ).execute().get('downloadUrl')

            if not url:
                return ""

            headers = {
                'range': 'bytes=%d-%d' % ( 
                    self._offset,
                    self._offset + length
                ) 
            }

            res, data = http.request(url, headers=headers)
            retry = res.status in [ 301, 302, 303, 307, 308 ] \
                and 'location' in res

            if retry: # pragma: no cover
                url = res['location'] 
                res, data = http.request(url, headers=headers) 

            if res.status in [ 200, 206 ]:
                self._offset += length
                return data

        return "" # pragma: no cover

    def write(self, data):
        """
        Writes data into the file at the current offset.

        Currently not supported by Google Drive API.
        """
        data = data # static_cast<void>(data) for pylint
        self._required_open()
        self._required_modes([ "w", "a" ])


class DrivePathCache(object):
    """
    Defines the Google Drive path caching class.
    """
    def __init__(self, data=None):
        self.__data = {}

        if data is not None:
            for key, val in data.iteritems():
                path = Drive().normpath(key)
                if path is None or not isinstance(val, dict):
                    continue

                self.__data[path] = val

    def put(self, path, data):
        """Places an item in the path cache"""
        path = Drive().normpath(path)
        self.__data[path] = data

    def get(self, path):
        """Retrieves an item from the path cache"""
        path = Drive().normpath(path)
        return self.__data.get(path)

    def clear(self, path):
        """Removes an item from the path cache"""
        path = Drive().normpath(path)
        if self.__data.has_key(path):
            del self.__data[path]

    def __repr__(self):
        return "DrivePathCache(%s)" % repr(self.__data)
        

class Drive(object):
    """Defines the singleton Google Drive API interface class."""
    def __new__(cls, *args):
        if not hasattr(cls, "_instance"):
            cls._instance = object.__new__(cls, *args)

        return cls._instance

    def __init__(self):
        debug("Initialising drive")

        self._service = None
        self._http = None
        self._credentials = None
        self._credential_storage = None
        self._pcache = DrivePathCache()

        debug("Initialisation complete")
     
    @staticmethod
    def unicode(strval):
        """
        Converts a string to unicode from any number of encodings that would
        ordinarily cause UnicodeDecodeError exceptions.  Only if an encoding
        is encountered that is not supported by Drive, is this exception type
        raised or propagated.
        """
        # First see if we need to decode it...
        strval_unicode = None

        if not isinstance(strval, basestring):
            strval = unicode(str(strval))

        if isinstance(strval, unicode):
            strval_unicode = strval
        else:
            for enc in ("utf-8", "latin-1"):
                try:
                    strval_unicode = strval.decode(enc)
                    break
                except UnicodeDecodeError: # pragma: no cover
                    pass

        if strval_unicode is None: # pragma: no cover
            raise UnicodeDecodeError("Failed to decode: %s" % repr(strval))

        return strval_unicode

    @staticmethod
    def utf8(strval):
        """
        Ensures non-utf8 encoded strings are re-encoded in utf8.  The
        utf8 encoded strings are returned, otherwise a UnicodeDecodeError
        is raised.
        """
        return Drive.unicode(strval).encode("utf-8")

    @contextmanager
    def service(self):
        """
        Establishes, caches and returns either a new or cached instance of a
        Google apiclient resource object, pertinent to a particular Google
        API; in our case, the Drive API.
        """
        if self._service is not None:
            yield self._service
            return

        storage = self._get_credential_storage()
        if storage is not None:
            credentials = storage.get()
        else:
            credentials = None

        if credentials is None:
            credentials = self._obtain_credentials()

        debug("Authenticating")
        import httplib2

        #if debug.enabled(): httplib2.debuglevel = 4

        http = credentials.authorize(
            httplib2.Http(cache = self._get_config_dir("http_cache"))
        )

        debug("Loading Google Drive service from config")

        from apiclient.discovery import build_from_document, DISCOVERY_URI
        
        debug("Downloading API service")

        import uritemplate
        url = uritemplate.expand(DISCOVERY_URI, {
            'api': 'drive',
            'apiVersion': 'v2'
        })
        res, content = http.request(url)

        apistr = None
        if res.status in [ 200, 202 ]:
            # API expires every minute.
            apistr = content

        if not apistr:
            raise NoServiceError

        debug("Building Google Drive service from document")
        self._service = build_from_document(
            apistr, http = http, base = DISCOVERY_URI
        )

        yield self._service

    def __del__(self): # pragma: no cover
        debug("Saving credentials...")
        credentials = self._credentials
        if credentials:
            storage = self._get_credential_storage()
            if storage is not None:
                storage.put(credentials)

        debug("My pid = %d" % os.getpid())

    def _get_config_dir(self, subdir = None):
        """Returns the path to the gsync config directory"""
        configdir = os.getenv('GSYNC_CONFIG_DIR',
            os.path.join(os.getenv('HOME', '~'), '.gsync')
        )
        debug("Config dir = %s" % configdir)

        if not os.path.exists(configdir):
            os.mkdir(configdir, 0700)

        if subdir is not None:
            configdir = os.path.join(configdir, subdir)

            if not os.path.exists(configdir):
                os.mkdir(configdir, 0700)

        return configdir

    def _get_config_file(self, name):
        """Returns the path to the gsync config file"""
        envname = re.sub(r'[^0-9A-Z]', '_', 'GSYNC_%s' % name.upper())
        val = os.getenv(envname, os.path.join(self._get_config_dir(), name))
        debug("Environment: %s=%s" % (envname, val))
        return val

    def _get_credential_storage(self):
        """Returns the oauth2client stored credentials"""

        storage = self._credential_storage
        if storage is not None:
            return storage

        debug("Loading storage")

        storagefile = self._get_config_file('credentials')

        if not os.path.exists(storagefile):
            open(storagefile, 'a+b').close() 

        from oauth2client.file import Storage
        storage = Storage(storagefile)
        self._credential_storage = storage

        return storage

    def _obtain_credentials(self):
        """
        Prompts the user for authentication tokens to create a local ticket
        or token, that can be used for all future Google Drive requests.
        """
        self._credentials = None

        # In order to gain authorization, we need to be running on a TTY.
        # Let's make sure before potentially hanging the process waiting for
        # input from a non existent user.
        if not sys.stdin.isatty():
            raise NoTTYError

        # Locate the client.json file.
        client_json = self._get_config_file("client.json")

        # Create the client.json file if not present.
        if not os.path.exists(client_json):
            try:
                from libgsync.drive.client_json import client_obj

                with open(client_json, "w") as fd:
                    fd.write(json.dumps(client_obj))

            except Exception, ex:
                debug("Exception: %s" % repr(ex))
                raise

        if not os.path.exists(client_json):
            raise FileNotFoundError(client_json)

        # Reresh token not available through config, so let's request a new
        # one using the app client ID and secret.  Here, we need to obtain an
        # auth URL that the user will need to visit to obtain the user code
        # needed to allow us to obtain a refresh token.
        from oauth2client.client import flow_from_clientsecrets
        flow = flow_from_clientsecrets(
            client_json,
            scope = 'https://www.googleapis.com/auth/drive',
            redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        )

        auth_uri = flow.step1_get_authorize_url()
        print("Authorization is required to access your Google Drive.")
        print("Navigate to the following URL:\n%s" % auth_uri)

        code = ""
        while not code:
            code = raw_input("Type in the received code: ")

        credentials = flow.step2_exchange(code)
        if credentials is None:
            raise ExchangeError

        self._credentials = credentials

        return credentials

    def walk(self, top, topdown=True, onerror=None, followlinks=False):
        """
        Walks the Google Drive directory structure one directory at a time
        and processes all files at each directory by yielding a tuple of
        the directory, list of directories and list of files.
        """

        join = os.path.join
        names = None

        debug("Walking: %s" % repr(top))

        try:
            names = self.listdir(top)
        except Exception, ex:
            debug.exception()
            debug("Exception: %s" % repr(ex))

            if onerror is not None:
                onerror(ex)
            return

        debug("Separating directories from files...")
        dirs, nondirs = [], []
        for name in names:
            if self.isdir(join(top, name)):
                dirs.append(name)
            else:
                nondirs.append(name)

        if topdown:
            yield top, dirs, nondirs

        debug("Iterating directories...")
        for name in dirs:
            new_path = join(top, name)
            for vals in self.walk(new_path, topdown, onerror, followlinks):
                yield vals

        debug("Yeilding on non-directories...")
        if not topdown:
            yield top, dirs, nondirs

    def is_rootpath(self, path):
        """
        Returns True if the path provided is the root of the Google Drive.
        """
        return bool(re.search(r'^drive:/+$', path) is not None)

    def is_drivepath(self, path):
        """
        Returns True if the path provided is path within the Google Drive.
        """
        return bool(re.search(r'^drive:/+', path) is not None)

    def validatepath(self, path):
        """
        Like 'is_drivepath' but raises a ValueError when the path is not a
        Google Drive path.
        """
        if not self.is_drivepath(path):
            raise ValueError("Invalid path: %s" % path)

    def strippath(self, path):
        """
        Strips the 'drive://' part from the path, creating a local POSIX
        path representation of the file.
        """
        return re.sub(r'^(?:drive:/*|/+)', '/', os.path.normpath(path))

    def normpath(self, path):
        """
        Opposite to the 'strippath' method, it ensures the path is prefixed
        with the 'drive://' prefix, creating the remote representation of the
        file path.
        """
        return re.sub(r'^(?:drive:/*|/+)', 'drive://', os.path.normpath(path))

    def pathlist(self, path):
        """
        Returns a list containing all of the elements of the path.  Like
        "/path/to/a/file".split("/"), except it is platform independent.
        """
        self.validatepath(path)

        pathlist = []
        path = self.strippath(path)

        while True:
            path, folder = os.path.split(path)
            if folder != "":
                pathlist.insert(0, folder)

            elif path != "":
                pathlist.insert(0, self.normpath(path))
                break

        return pathlist

    def _find_entity(self, name, ents):
        """
        Finds an entity in a list of entities returned in a Drive query.
        """
        debug("Iterating %d entities to find %s" % (len(ents), repr(name)))
        name = Drive.unicode(name)
        for ent in ents:
            entname = ent.get('title', u"")

            debug("comparing %s to %s" % (repr(name), repr(entname)))
            if name == entname:
                debug("Found %s" % repr(name))
                return ent

        return None

    def stat(self, path):
        """
        Performs a remote 'stat' on the file at the given path.  Returns the
        file info object, or None if the file does not exist.
        """
        self.validatepath(path)
        path = self.normpath(path)

        # If it is cached, we can obtain it there.
        debug("Checking pcache for path: %s" % repr(path))
        ent = self._pcache.get(path)

        if ent is not None:
            debug("Found path in path cache: %s" % repr(path))
            return DriveFile(path = Drive.unicode(path), **ent)

        # First list root and walk to the requested file from there.
        ent = DriveFile(
            path = Drive.unicode(self.normpath('/')),
            id = 'root',
            title = '/',
            mimeType = MimeTypes.FOLDER,
            modifiedDate = "Thu, 01 Jan 1970 00:00:00 +0000"
        )

        # User has requested root directory
        if self.is_rootpath(path):
            debug("Path is root: %s" % repr(path))
            return ent

        # Break down the path and enumerate each folder.
        # Walk the path until we find the file we are looking for.
        paths = self.pathlist(path)
        pathslen = len(paths)

        debug("Got %d paths from pathlist(%s)" % (pathslen, repr(path)))
        debug("Got paths: %s" % repr(paths))

        for i in xrange(1, pathslen):
            searchpath = os.path.join(*paths[:i])
            searchname = paths[i]
            search = os.path.join(searchpath, searchname)

            debug("Searching for %s in path %s" % (
                repr(searchname), repr(searchpath)
            ))

            # First check our cache to see if we already have it.
            parent_id = str(ent['id'])

            debug("Checking pcache for path: %s" % repr(search))
            ent = self._pcache.get(search)
            if ent is None:
                debug(" * nothing found")
                ents = self._query(parent_id=parent_id)

                debug("Got %d entities back" % len(ents))

                if len(ents) == 0:
                    return None

                ent = self._find_entity(searchname, ents)

            if ent is None:
                return None

            # Update path cache.
            if self._pcache.get(search) is None:
                debug("Updating path cache: %s" % repr(search), 3)
                self._pcache.put(search, ent)

            if search == path:
                debug("Found %s" % repr(search))
                drive_file = DriveFile(path = Drive.unicode(path), **ent)

                debug(" * returning %s" % repr(drive_file), 3)
                return drive_file

        # Finally, couldn't find anything, raise an error?
        return None

    def mkdir(self, path):
        """
        Creates a directory at the specified path and any parent directories,
        if the path specified does not already exist.
        """
        debug("path = %s" % repr(path))

        self.validatepath(path)

        spath = self.strippath(path)
        normpath = self.normpath(spath)

        debug("spath = %s" % repr(spath))
        debug("normpath = %s" % repr(normpath))

        dirname, basename = os.path.split(normpath)
        debug("dirname = %s, basename = %s" % (
            repr(dirname), repr(basename)
        ))
        if dirname in [ "/", "drive:" ]:
            parent_id = "root"
        else:
            parent = self.stat(dirname)
            debug("Failed to stat directory: %s" % repr(dirname))

            if not parent:
                if normpath != dirname:
                    parent = self.mkdir(dirname)

                if not parent:
                    debug("Failed to create parent: %s" % repr(dirname))
                    return None

            debug("Got parent: %s" % repr(parent))
            parent_id = parent.id

        debug("Creating directory: %s" % repr(normpath))

        with self.service() as service:
            info = service.files().insert(
                body = {
                    'title': basename,
                    'mimeType': MimeTypes.FOLDER,
                    'parents': [{ 'id': parent_id }]
                }
            ).execute()

            if info:
                self._pcache.put(path, info)
                ent = DriveFile(path = Drive.unicode(normpath), **info)
                return ent

        raise IOError("Failed to create directory: %s" % path)

    def isdir(self, path):
        """Returns True if the file at the specified path is a directory"""
        ent = self.stat(path)
        return ent is not None and ent.mimeType == MimeTypes.FOLDER
    
    def listdir(self, path):
        """Returns a list of directory contents at the specified location"""
        ent = self.stat(path)
        ents = self._query(parent_id=str(ent.id))

        names = []
        for ent in ents:
            names.append(ent['title'])

        return names

    def open(self, path, mode = "r"):
        """
        Returns a DriveFileObject as a python file type object wrapper to
        the remote file specified by the path.  See DriveFileObject.
        """
        return DriveFileObject(path, mode)

    def delete(self, path, skip_trash=False):
        """
        Deletes a file at the specified location.  By default, the file will
        be moved to trash.  If skip_trash is set to True, the file is deleted
        and will not be sent to trash.
        """
        info = self.stat(path)
        if info is None:
            return

        with self.service() as service:
            if skip_trash:
                debug("Deleting: %s (id: %s)" % (repr(path), info.id))
                service.files().delete(fileId=info.id).execute()
            else:
                debug("Trashing: %s (id: %s)" % (repr(path), info.id))
                service.files().trash(fileId=info.id).execute()

            return

        debug("Deletion failed")

    def create(self, path, properties):
        """
        Creates an empty remote file at the specified location.
        """
        debug("Create file %s" % repr(path))

        # Get the parent directory.
        dirname = os.path.dirname(path)
        info = self.stat(dirname)
        if info is None:
            return None

        parent_id = info.id

        debug(" * parent_id = %s" % repr(parent_id))

        # Get the file info and delete existing file.
        info = self.stat(path)
        if info is not None:
            debug(" * deleting existing...")
            self.delete(path)

        debug(" * merging properties...")
        body = {}
        for key, val in properties.iteritems():
            body[key] = Drive.utf8(val)

        # Retain the title from the path being created.
        body['title'] = Drive.utf8(os.path.basename(path))

        if parent_id:
            body['parents'] = [{'id': parent_id}]

        debug(" * trying...")
        with self.service() as service:
            ent = service.files().insert(
                body = body,
                media_body = ""
            ).execute()

            # Clear the cache and update the path cache
            self._pcache.put(path, ent)

            debug(" * file created")
            return ent

        debug("Creation failed")
        return None

    def update(self, path, properties, **kwargs):
        """
        Updates the content and attributes of a remote file.
        """
        progress_callback = kwargs.get('progress_callback')
        options = kwargs.get('options', {})

        info = self.stat(path)
        if not info:
            raise FileNotFoundError(path)

        debug("Updating: %s" % repr(path))

        # Merge properties
        for key, val in properties.iteritems():
            # Do not update the ID, always use the path obtained ID.
            if key == 'id':
                continue

            debug(" * with: %s = %s" % (repr(key), repr(val)))
            setattr(info, key, Drive.utf8(val))

        with self.service() as service:
            res = None
            req = service.files().update(
                fileId=info.id,
                body=info.copy(),
                setModifiedDate=options.get('setModifiedDate', False),
                newRevision=True,
                media_body=kwargs.get('media_body')
            )

            if progress_callback is None:
                res = req.execute()

            else:
                try:
                    while res is None:
                        debug(" * uploading next chunk...")

                        status, res = req.next_chunk()
                        if status:
                            progress_callback(status)

                        elif res:
                            file_size = int(res['fileSize'])
                            progress_callback(
                                MediaUploadProgress(file_size, file_size)
                            )

                except Exception, ex:
                    debug("Exception: %s" % str(ex))
                    debug.exception()

            # Refresh the cache with the latest revision
            self._pcache.put(path, res)

            return res

        debug("Update failed")
        raise Exception("Update failed")
    
    def _query(self, **kwargs):
        """
        Performs a query against the Google Drive, returning an entity list
        that was returned by the server.  This function acts as a proxy to
        the Google Drive, simplifying requests.
        """
        parent_id = kwargs.get("parent_id")
        mimetype = kwargs.get("mimetype")
        file_id = kwargs.get("id")
        include_trash = kwargs.get("include_trash", False)

        page_token = None
        query, ents = [], []
        param = {}

        if file_id is not None:
            query.append('id = "%s"' % file_id)
        elif parent_id is not None:
            query.append('"%s" in parents' % parent_id)

            if mimetype is not None:
                query.append('mimetype = "%s"' % mimetype)

        if not include_trash:
            query.append('trashed = false')

        if len(query) > 0:
            param['q'] = ' and '.join(query)

        with self.service() as service:
            while True:
                if page_token:
                    param['pageToken'] = page_token

                debug("Executing query: %s" % repr(param))

                files = service.files().list(**param).execute()

                debug("Query returned %d files" % len(files))

                ents.extend(files['items'])
                page_token = files.get('nextPageToken')

                if not page_token:
                    break

        return ents
