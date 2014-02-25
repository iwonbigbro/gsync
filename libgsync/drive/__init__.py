# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, sys, re, datetime, shelve, time

try: import simplejson as json
except ImportError: import json

from oauth2client.client import OAuth2Credentials
from libgsync.output import verbose, debug
from libgsync.drive.mimetypes import MimeTypes
from libgsync.drive.file import DriveFile

# Set to True for strict positional parameter exceptions in oauth2client
try:
    import gflags
    if False:
        gflags.FLAGS['positional_parameters_enforcement'].value = 'EXCEPTION'
    else:
        gflags.FLAGS['positional_parameters_enforcement'].value = 'IGNORE'
except Exception:
    pass

if debug.enabled():
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

class ENoTTY(Exception):
    pass

class EGetAuthURL(Exception):
    pass

class EExchange(Exception):
    pass

class EInvalidRequest(Exception):
    pass

class EFileNotFound(Exception):
    def __init__(self, filename):
        self.filename = filename

    def __str__(self):
        return "File not found: %s" % repr(self.filename)


class DriveFileObject(object):
    def __init__(self, path, mode = "r"):
        # Public
        self.closed = False
        self.description = ""
        self.modifiedDate = datetime.datetime.now().isoformat()

        # Private
        drive = Drive()
        path = drive.normpath(path)

        self._drive = drive
        self._path = path
        self._info = self._drive.stat(path)
        self._offset = 0
        self._size = 0
        self._mode = mode
        self._mimeType = MimeTypes.BINARY_FILE
        self._parentId = None

        # Only mode support at present
        if mode != "r":
            raise IOError("Unsupported mode: %s" % mode)

        if self._info:
            # File size is set to None for empty documents.
            if self._info.fileSize is not None:
                self._size = int(self._info.fileSize)

            self.description = self._info.description

        dirname, filename = os.path.split(path)
        self._dirname = dirname
        self._filename = filename
        self._parentInfo = self._drive.stat(dirname)

    def __repr__(self):
        return "%s(%s, %s)" % (
            self.__class__.__name__, repr(self._path), repr(self._mode)
        )

    def _requiredOpen(self):
        if self.closed:
            raise ValueError("File is closed: %s" % self._path)

    def _requireModes(self, modes):
        if self._mode in modes:
            raise ValueError("Operation not permitted: %s()" % name)

    def revisions(self):
        try:
            revisions = self._drive.service().revisions().list(
                fileId=self._info.id
            ).execute()
            return revisions.get('items', [])

        except Exception, e:
            debug.exception(e)
            return None

    def mimetype(self, mimeType = None):
        if mimetype is not None:
            self._mimeType = mimeType
        return self._mimeType

    def close(self):
        self.closed = True

    def flush(self):
        pass

    def seek(self, offset, whence = 0):
        self._requiredOpen()

        if whence == 0:
            self._offset = offset
        elif whence == 1:
            self._offset += offset
        elif whence == 2:
            self._offset = self._size - offset

    def tell(self):
        self._requiredOpen()

        return self._offset

    # A pseudo function really, has no effect if no data is written after
    # calling this method.
    def truncate(self, size = None):
        self._requiredOpen()

        if size is None:
            size = self._offset
        self._size = size

    def read(self, length = None):
        if self._info is None: return ""

        self._requiredOpen()

        service = self._drive.service()
        http = service._http
        http.follow_redirects = False 

        if length is None:
            length = self._size - self._offset

        if length <= 0: return ""

        url = service.files().get(
            fileId=self._info.id
        ).execute().get('downloadUrl')

        if not url: return ""

        headers = {
            'range': 'bytes=%d-%d' % ( 
                self._offset,
                self._offset + length
            ) 
        }

        res, data = http.request(url, headers=headers)

        if res.status in [ 301, 302, 303, 307, 308 ] and 'location' in res: 
            url = res['location'] 
            res, data = http.request(url, headers=headers) 

        if res.status in [ 200, 206 ]:
            self._offset += length
            return data

        return ""

    def write(self, data):
        self._requiredOpen()

        raise Exception("Not currently supported by Google Drive API v2")


class DrivePathCache(object):
    def __init__(self, data={}):
        self.__data = data

    def put(self, path, data):
        path = Drive().normpath(path)
        self.__data[path] = data

    def get(self, path):
        path = Drive().normpath(path)
        return self.__data.get(path)

    def clear(self, path):
        path = Drive().normpath(path)
        if self.__data.has_key(path):
            del self.__data[path]

    def __repr__(self):
        return "DrivePathCache(%s)" % repr(self.__data)
        

class _Drive(object):
    def __init__(self):
        debug("Initialising drive")

        self._service = None
        self._http = None
        self._credentials = None
        self._service = None
        self._credentialStorage = None
        self.reinit()

        debug("Initialisation complete")

    def reinit(self):
        # Load parent folder cache
        self._pcache = DrivePathCache()
     
    @staticmethod
    def unicode(s):
        # First see if we need to decode it...
        su = None

        if not isinstance(s, basestring):
            s = unicode(str(s))

        if isinstance(s, unicode):
            su = s
        else:
            for enc in ("utf-8", "latin-1"):
                try:
                    su = s.decode(enc)
                    break
                except UnicodeDecodeError:
                    pass

        if su is None:
            raise UnicodeDecodeError("Failed to decode: %s" % repr(s))

        return su

    @staticmethod
    def utf8(s):
        return _Drive.unicode(s).encode("utf-8")

    def service(self):
        if self._service is not None:
            return self._service

        storage = self._getCredentialStorage()
        if storage is not None:
            credentials = storage.get()
        else:
            credentials = None

        if credentials is None:
            credentials = self._obtainCredentials()

        debug("Authenticating")
        import httplib2

        #if debug.enabled(): httplib2.debuglevel = 4

        http = credentials.authorize(
            httplib2.Http(cache = self._getConfigDir("http_cache"))
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
            return None

        debug("Building Google Drive service from document")
        self._service = build_from_document(
            apistr, http = http, base = DISCOVERY_URI
        )

        return self._service

    def __del__(self):
        debug("Saving credentials...")
        credentials = self._credentials
        if credentials:
            storage = self._getCredentialStorage()
            if storage is not None:
                storage.put(credentials)

        debug("My pid = %d" % os.getpid())

    def _getConfigDir(self, subdir = None):
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

    def _getConfigFile(self, name):
        envname = re.sub(r'[^0-9A-Z]', '_', 'GSYNC_%s' % name.upper())
        val = os.getenv(envname, os.path.join(self._getConfigDir(), name))
        debug("Environment: %s=%s" % (envname, val))
        return val

    def _getCredentialStorage(self):
        storage = self._credentialStorage
        if storage is not None:
            return storage

        debug("Loading storage")

        storagefile = self._getConfigFile('credentials')

        if not os.path.exists(storagefile):
            open(storagefile, 'a+b').close() 

        from oauth2client.file import Storage
        storage = Storage(storagefile)
        self._credentialStorage = storage

        return storage

    def _obtainCredentials(self):
        self._credentials = None

        # In order to gain authorization, we need to be running on a TTY.
        # Let's make sure before potentially hanging the process waiting for
        # input from a non existent user.
        if not sys.stdin.isatty():
            raise ENoTTY

        # Locate the client.json file.
        client_json = self._getConfigFile("client.json")

        # Create the client.json file if not present.
        if not os.path.exists(client_json):
            try:
                from libgsync.drive.client_json import client_obj

                with open(client_json, "w") as f:
                    f.write(json.dumps(client_obj))

            except Exception, e:
                debug("Exception: %s" % repr(e))
                raise

        if not os.path.exists(client_json):
            raise EFileNotFound(client_json)

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

        while True:
            code = raw_input("Type in the received code: ")
            if code: break

        credentials = flow.step2_exchange(code)
        if credentials is None:
            raise EExchange

        self._credentials = credentials

        return credentials

    def walk(self, top, topdown = True, onerror = None, followlinks = False):
        join = os.path.join
        names = None

        debug("Walking: %s" % repr(top))

        try:
            names = self.listdir(top)
        except Exception, e:
            debug.exception()
            debug("Exception: %s" % repr(e))

            if onerror is not None:
                onerror(e)
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
            for x in self.walk(new_path, topdown, onerror, followlinks):
                yield x

        debug("Yeilding on non-directories...")
        if not topdown:
            yield top, dirs, nondirs

    def is_rootpath(self, path):
        return bool(re.search(r'^drive:/+$', path) is not None)

    def is_drivepath(self, path):
        return bool(re.search(r'^drive:/+', path) is not None)

    def validatepath(self, path):
        if not self.is_drivepath(path):
            raise ValueError("Invalid path: %s" % path)

    def strippath(self, path):
        return re.sub(r'^(?:drive:/*|/+)', '/', os.path.normpath(path))

    def normpath(self, path):
        return re.sub(r'^(?:drive:/*|/+)', 'drive://', os.path.normpath(path))

    def pathlist(self, path):
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

    def _findEntity(self, name, ents):
        debug("Iterating %d entities to find %s" % (len(ents), repr(name)))
        name = _Drive.unicode(name)
        for ent in ents:
            entname = ent.get('title', u"")

            debug("comparing %s to %s" % (repr(name), repr(entname)))
            if name == entname:
                debug("Found %s" % repr(name))
                return ent

        return None

    def stat(self, path):
        self.validatepath(path)
        path = self.normpath(path)

        # If it is cached, we can obtain it there.
        debug("Checking pcache for path: %s" % repr(path))
        ent = self._pcache.get(path)

        if ent is not None:
            debug("Found path in path cache: %s" % repr(path))
            return DriveFile(path = _Drive.unicode(path), **ent)

        # First list root and walk to the requested file from there.
        ent = DriveFile(
            path = _Drive.unicode(self.normpath('/')),
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
            parentId = str(ent['id'])

            debug("Checking pcache for path: %s" % repr(search))
            ent = self._pcache.get(search)
            if ent is None:
                debug(" * nothing found")
                ents = self._query(parentId = parentId)

                debug("Got %d entities back" % len(ents))

                if len(ents) == 0: return None

                ent = self._findEntity(searchname, ents)

            if ent is None:
                return None

            # Update path cache.
            if self._pcache.get(search) is None:
                debug("Updating path cache: %s" % repr(search), 3)
                self._pcache.put(search, ent)

            if search == path:
                debug("Found %s" % repr(search))
                df = DriveFile(path = _Drive.unicode(path), **ent)

                debug(" * returning %s" % repr(df), 3)
                return df

        # Finally, couldn't find anything, raise an error?
        return None

    def mkdir(self, path):
        debug("path = %s" % repr(path))

        self.validatepath(path)

        spath = self.strippath(path)
        normpath = self.normpath(spath)

        debug("spath = %s" % repr(spath))
        debug("normpath = %s" % repr(normpath))

        try:
            dirname, basename = os.path.split(normpath)
            debug("dirname = %s, basename = %s" % (
                repr(dirname), repr(basename)
            ))
            if dirname in [ "/", "drive:" ]:
                parentId = "root"
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
                parentId = parent.id

            debug("Creating directory: %s" % repr(normpath))
 
            info = self.service().files().insert(
                body = {
                    'title': basename,
                    'mimeType': MimeTypes.FOLDER,
                    'parents': [{ 'id': parentId }]
                }
            ).execute()

            if info:
                self._pcache.put(path, info)
                ent = DriveFile(path = _Drive.unicode(normpath), **info)
                return ent
        except Exception, e:
            debug.exception()
            debug("Failed to create directory: %s" % repr(e))

        raise IOError("Failed to create directory: %s" % path)

    def isdir(self, path):
        ent = self.stat(path)
        if ent is None: return False
        if ent.mimeType != MimeTypes.FOLDER: return False

        return True
    
    def listdir(self, path):
        ent = self.stat(path)
        ents = self._query(parentId = str(ent.id))

        names = []
        for ent in ents:
            names.append(ent['title'])

        return names

    def open(self, path, mode = "r"):
        return DriveFileObject(path, mode)

    def delete(self, path, skipTrash = False):
        info = self.stat(path)
        if info is None: return

        try:
            if skipTrash:
                debug("Deleting: %s (id: %s)" % (repr(path), info.id))
                self.service().files().delete(
                    fileId = info.id
                ).execute()
            else:
                debug("Trashing: %s (id: %s)" % (repr(path), info.id))
                self.service().files().trash(
                    fileId = info.id
                ).execute()
        except Exception, e:
            debug("Deletion failed: %s" % repr(e))

    def create(self, path, properties):
        debug("Create file %s" % repr(path))

        # Get the parent directory.
        dirname, basename = os.path.split(path)
        info = self.stat(dirname)
        if info is None: return None

        parentId = info.id

        debug(" * parentId = %s" % repr(parentId))

        try:
            # Get the file info and delete existing file.
            info = self.stat(path)
            if info is not None:
                debug(" * deleting existing...")
                self.delete(path)

            debug(" * merging properties...")
            body = {}
            for k, v in properties.iteritems():
                body[k] = _Drive.utf8(v)

            # Retain the title from the path being created.
            body['title'] = _Drive.utf8(os.path.basename(path))

            if parentId:
                body['parents'] = [{'id': parentId}]

            debug(" * trying...")
            ent = self.service().files().insert(
                body = body,
                media_body = ""
            ).execute()

            # Clear the cache and update the path cache
            self._pcache.put(path, ent)

            debug(" * file created")
            return ent
        except Exception, e:
            debug("Creation failed: %s" % repr(e))

        return None

    def update(self,
        path, properties,
        media_body = None,
        progress_callback = None,
        options = {}
    ):
        info = self.stat(path)

        if not info:
            debug("No such file: %s" % repr(path))
            return None

        debug("Updating: %s" % repr(path))

        # Merge properties
        for k, v in properties.iteritems():
            # Do not update the ID, always use the path obtained ID.
            if k == 'id': continue

            debug(" * with: %s = %s" % (repr(k), repr(v)))
            setattr(info, k, _Drive.utf8(v))

        debug("mdeia_body type = %s" % type(media_body))

        try:
            req = self.service().files().update(
                fileId = info.id,
                body = info.dict(),
                setModifiedDate = options.get('setModifiedDate', False),
                newRevision = True,
                media_body = media_body
            )

            if progress_callback is None:
                res = req.execute()

            else:
                status, res = None, None
                while res is None:
                    debug(" * uploading next chunk...")

                    try:
                        status, res = req.next_chunk()
                    except Exception, e:
                        debug("Exception: %s" % str(e))
                        debug.exception()
                        break

                    if status:
                        progress_callback(status)

            # Refresh the cache with the latest revision
            self._pcache.put(path, res)

            return res

        except Exception, e:
            debug("Update failed: %s" % repr(e))
            debug.exception()
            raise
    
    def _query(self, **kwargs):
        parentId = kwargs.get("parentId")
        mimeType = kwargs.get("mimeType")
        fileId = kwargs.get("id")
        includeTrash = kwargs.get("includeTrash", False)
        result = []

        page_token = None
        service = self.service()
        query, ents = [], []
        param = {}

        if fileId is not None:
            query.append('id = "%s"' % fileId)
        elif parentId is not None:
            query.append('"%s" in parents' % parentId)

            if mimeType is not None:
                query.append('mimeType = "%s"' % mimeType)

        if not includeTrash:
            query.append('trashed = false')

        if len(query) > 0:
            param['q'] = ' and '.join(query)

        while True:
            if page_token:
                param['pageToken'] = page_token

            debug("Executing query: %s" % repr(param))

            files = service.files().list(**param).execute()

            debug("Query returned %d files" % len(files))

            ents.extend(files['items'])
            page_token = files.get('nextPageToken')

            if not page_token: break

        return ents

# The fake Drive() constructor and global drive instance.
g_drive = None

def Drive():
    global g_drive
    if g_drive is None:
        g_drive = _Drive()

    return g_drive
