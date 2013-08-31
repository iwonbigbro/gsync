# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, sys, re, datetime, shelve, time

try: import simplejson as json
except ImportError: import json

from oauth2client.client import OAuth2Credentials
from libgsync.output import verbose, debug
from libgsync.drive.mimetypes import MimeTypes
from libgsync.drive.file import DriveFile

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
        return "File not found: %s" % self.filename


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

    def _requiredOpen(self):
        if self.closed:
            raise ValueError("File is closed: %s" % self._path)

    def _requireModes(self, modes):
        if self._mode in modes:
            raise ValueError("Operation not permitted: %s()" % name)

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


class _Drive():
    def __init__(self):
        debug("Initialising drive")

        self._service = None
        self._http = None
        self._credentials = None
        self._service = None
        self._credentialStorage = None
        
        # Load Google Drive local cache (currently disabled)
        cfg = self._getConfigFile("drive.v2.gcache")
        self._gcache = shelve.open(cfg, flag = 'n')

        # Load parent folder cache (currently disabled)
        cfg = self._getConfigFile("drive.v2.pcache")
        self._pcache = shelve.open(cfg, flag = 'n')

        debug("Initialisation complete")

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

        if debug.enabled():
            httplib2.debuglevel = 4

        http = credentials.authorize(
            httplib2.Http(cache = self._getConfigDir("http_cache"))
        )

        debug("Loading Google Drive service from config")

        cfg = self._getConfigFile("drive.v2.service")
        api = shelve.open(cfg)
        apistr = None
        now = int(time.time())

        from apiclient.discovery import build_from_document, DISCOVERY_URI
        if now < int(api.get('expires', 0)):
            apistr = json.dumps(dict(api))
        else:
            debug("API has expired")

        if not apistr:
            debug("Downloading API service")

            import uritemplate
            url = uritemplate.expand(DISCOVERY_URI, {
                'api': 'drive',
                'apiVersion': 'v2'
            })
            res, content = http.request(url)

            if res.status in [ 200, 202 ]:
                # API expires every minute.
                apistr = content
                api.update(json.loads(apistr))
                api['expires'] = int(time.time()) + 60

        api.close()

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

        debug("Saving gcache (%d items)..." % len(self._gcache))
        self._gcache.close()

        debug("Saving pcache (%d items)..." % len(self._pcache))
        self._pcache.close()

        debug("My pid = %d" % os.getpid())

    def _getConfigDir(self, subdir = None):
        homedir = os.getenv('HOME', '~')
        configdir = os.path.join(homedir, '.gsync')

        if not os.path.exists(configdir):
            os.mkdir(configdir, 0700)

        if subdir is not None:
            configdir = os.path.join(configdir, subdir)

            if not os.path.exists(configdir):
                os.mkdir(configdir, 0700)

        return configdir

    def _getConfigFile(self, name):
        return os.path.join(self._getConfigDir(), name)

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

        # Reresh token not available through config, so let's request a new
        # one using the app client ID and secret.  Here, we need to obtain an
        # auth URL that the user will need to visit to obtain the user code
        # needed to allow us to obtain a refresh token.
        from oauth2client.client import flow_from_clientsecrets
        flow = flow_from_clientsecrets(
            os.path.join(os.path.dirname(__file__), 'data', 'client.json'),
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

        debug("Walking: %s" % top)

        try:
            names = self.listdir(top)
        except Exception, e:
            debug.exception()
            debug("Exception: %s" % str(e))

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
        debug("Iterating %d entities to find %s" % (len(ents), name))
        for ent in ents:
            entname = ent.get('title', "")

            if name == entname:
                debug("Found %s" % name)
                return ent

        return None

    def stat(self, path):
        self.validatepath(path)
        path = self.normpath(path)

        # If it is cached, we can obtain it there.
        debug("Checking pcache for path: %s" % path)
        ent = self._pcache.get(str(path))

        if ent is not None:
            debug("Found path in path cache: %s" % path)
            return DriveFile(path = path, **ent)

        # First list root and walk to the requested file from there.
        ent = DriveFile(
            path = self.normpath('/'),
            id = 'root',
            title = '/',
            mimeType = MimeTypes.FOLDER
        )

        # User has requested root directory
        if self.is_rootpath(path):
            debug("Path is root: %s" % path)
            return ent

        # Break down the path and enumerate each folder.
        # Walk the path until we find the file we are looking for.
        paths = self.pathlist(path)
        pathslen = len(paths)

        debug("Got %d paths from pathlist(%s)" % (pathslen, path))
        debug("Got paths: %s" % paths)

        for i in xrange(1, pathslen):
            searchpath = os.path.join(*paths[:i])
            searchname = paths[i]
            search = str(os.path.join(searchpath, searchname))

            debug("Searching for %s in path %s" % (searchname, searchpath))

            # First check our cache to see if we already have it.
            parentId = str(ent['id'])

            debug("Checking pcache for path: %s" % search)
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
                debug("Updating path cache: %s" % search)
                self._pcache[search] = ent

            if search == path:
                debug("Found %s" % search)
                debug(" * ent: %s" % ent)
                df = DriveFile(path = path, **ent)
                debug(" * returning %s" % df)
                return df

        # Finally, couldn't find anything, raise an error.
        return None

    def rm(self, path, recursive=False):
        pass
    
    def mkdir(self, path):
        debug("path = %s" % path)

        self.validatepath(path)

        spath = self.strippath(path)
        normpath = self.normpath(spath)

        debug("spath = %s" % spath)
        debug("normpath = %s" % normpath)

        try:
            dirname, basename = os.path.split(normpath)
            debug("dirname = '%s', basename = '%s'" % (dirname, basename))
            if dirname in [ "/", "drive:" ]:
                parentId = "root"
            else:
                parent = self.stat(dirname)
                debug("Failed to stat directory: %s" % dirname)

                if not parent:
                    if normpath != dirname:
                        parent = self.mkdir(dirname)

                    if not parent:
                        debug("Failed to create parent: %s" % dirname)
                        return None

                debug("Got parent: %s" % repr(parent))
                parentId = parent.id

            debug("Creating directory: %s" % normpath)
 
            info = self.service().files().insert(
                body = {
                    'title': basename,
                    'mimeType': MimeTypes.FOLDER,
                    'parents': [{ 'id': parentId }]
                }
            ).execute()

            if info:
                self._clearCache(path)
                self._pcache[path] = info
                ent = DriveFile(path = normpath, **info)
                return ent
        except Exception, e:
            debug.exception()
            debug("Failed to create directory: %s" % str(e))

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
                debug("Deleting: %s (id: %s)" % (path, info.id))
                self.service().files().delete(
                    fileId = info.id
                ).execute()
            else:
                debug("Trashing: %s (id: %s)" % (path, info.id))
                self.service().files().trash(
                    fileId = info.id
                ).execute()
        except Exception, e:
            debug("Deltion failed: %s" % str(e))

        self._clearCache(path)

    def create(self, path, properties):
        # Get the parent directory.
        dirname, basename = os.path.split(path)
        info = self.stat(dirname)
        if info is None: return None

        parentId = info.id

        # Get the file info and delete existing file.
        info = self.stat(path)
        if info is not None:
            self.delete(path)

        body = {}
        for k, v in properties.iteritems():
            body[k] = str(v)

        if parentId:
            body['parents'] = [{'id': parentId}]

        try:
            ent = self.service().files().insert(
                body = body,
                media_body = ""
            ).execute()

            # Clear the cache and update the path cache
            self._clearCache(path)
            self._pcache[path] = ent

            return ent
        except Exception, e:
            debug("Creation failed: %s" % str(e))

        return None

    def update(self, path, properties, media_body = None):
        info = self.stat(path)

        if not info:
            debug("No such file: %s" % path)
            return None

        debug("Updating: %s" % info)

        # Merge properties
        for k, v in properties.iteritems():
            # Do not update the ID, always use the path obtained ID.
            if k == 'id': continue

            debug(" * with: %s = %s" % (k, v))
            setattr(info, k, v)

        try:
            return self.service().files().update(
                fileId = info.id,
                body = info.dict(),
                newRevision = True,
                media_body = media_body
            ).execute()
        except Exception, e:
            debug("Update failed: %s" % str(e))
            debug.stack()
            return None
    
    def _clearCache(self, path):
        debug("Clearing path cache entries for '%s'..." % path)
        if self._pcache.get(path):
            debug("    * delting: %s" % path)
            del self._pcache[path]

        info = self.stat(path)
        if info is None: return

        strInfoId = str(info.id)

        debug("Clearing Google cache entries...")
        if self._gcache.get(strInfoId):
            debug("    * delting: %s" % strInfoId)
            del self._gcache[strInfoId]

        # Parent cache must also be cleared
        for p in info.parents:
            pid = str(p['id'])
            if self._gcache.get(pid):
                debug("    * delting: %s" % pid)
                del self._gcache[pid]

    def _query(self, **kwargs):
        parentId = kwargs.get("parentId")
        mimeType = kwargs.get("mimeType")
        fileId = kwargs.get("id")
        result = []

        if parentId is not None:
            debug("Checking gcache for parentId: %s" % parentId)
            cached = self._gcache.get(parentId, None)

            if cached is not None:
                result.extend(cached)
                return result

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

        if len(query) > 0:
            param['q'] = ' and '.join(query)

        while True:
            if page_token:
                param['pageToken'] = page_token

            debug("Executing query: %s" % str(param))

            files = service.files().list(**param).execute()

            debug("Query returned %d files" % len(files))

            ents.extend(files['items'])
            page_token = files.get('nextPageToken')

            if not page_token: break

        debug("Updating google cache: %s (%d items)" % (parentId, len(ents)))
        self._gcache[parentId] = ents

        debug("My pid = %d" % os.getpid())

        return ents

# The fake Drive() constructor and global drive instance.
g_drive = None

def Drive():
    global g_drive
    if g_drive is None:
        g_drive = _Drive()

    return g_drive
