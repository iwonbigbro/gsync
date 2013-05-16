# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, sys
from oauth2client.client import OAuth2Credentials
from libgsync.output import verbose, debug
from libgsync.drive.mimetypes import MimeTypes

class ENoTTY(Exception):
    pass

class EGetAuthURL(Exception):
    pass

class EExchange(Exception):
    pass

class EFileNotFound(Exception):
    def __init__(self, filename):
        self.filename = filename

    def __str__(self):
        return "File not found: %s" % self.filename


class Drive():
    _credentials = None
    _service = None
    _storage = None
    _gcache = {}
    _pcache = {}

    def __init__(self):
        storage = self._getStorage()
        if storage is not None:
            credentials = storage.get()
        else:
            credentials = None

        if credentials is None:
            credentials = self._obtainCredentials()

        import httplib2
        http = credentials.authorize(httplib2.Http())

        from apiclient.discovery import build
        self._service = build('drive', 'v2', http = http)


    def __del__(self):
        credentials = self._credentials
        if credentials:
            storage = self._getStorage()
            if storage is not None:
                storage.put(credentials)


    def _getStorage(self):
        storage = self._storage
        if storage is not None:
            return storage

        homedir = os.getenv('HOME', '~')
        storagedir = os.path.join(homedir, '.gsync')
        storagefile = os.path.join(storagedir, 'credentials')

        if not os.path.exists(storagedir):
            os.mkdir(storagedir, 0700)

        if not os.path.exists(storagefile):
            open(storagefile, 'a+b').close() 

        from oauth2client.file import Storage
        storage = Storage(storagefile)
        self._storage = storage

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

        debug("Walking: %s" % top)

        try:
            names = self.listdir(top)
        except Exception, e:
            debug("Exception: %s" % str(e))

            if onerror is not None:
                onerror(e)
            return

        dirs, nondirs = [], []
        for name in names:
            if self.isdir(join(top, name)):
                dirs.append(name)
            else:
                nondirs.append(name)

        if topdown:
            yield top, dirs, nondirs

        for name in dirs:
            new_path = join(top, name)
            for x in self.walk(new_path, topdown, onerror, followlinks):
                yield x

        if not topdown:
            yield top, dirs, nondirs


    def stat(self, path):
        if path[0] != '/':
            raise EFileNotFound(path)

        # If it is cached, we can obtain it there.
        pcache = self._pcache
        ent = pcache.get(path, None)
        if ent is not None:
            debug("Loading from path cache: %s" % path)
            return ent

        # First list root and walk to the requested file from there.
        ents = self._query(parentId = 'root')
        if len(ents) == 0:
            raise EFileNotFound(path)

        join, split = os.path.join, os.path.split

        # Break down the path and enumerate each folder.
        paths = []
        while True:
            path, folder = split(path)
            if folder != "":
                paths.append(folder)
            elif path != "":
                paths.append(path)
                break

        # Walk the path until we find the file we are looking for.
        last = False
        while not last:
            d = paths.pop()
            last = (len(paths) == 0)

            for ent in ents:
                name = ent['title']
                path = join("/", d, name)

                # Update path based cache.
                debug("Updating path cache: %s" % path)
                pcache[path] = ent

                if d == name:
                    if last:
                        return ent

                    ents = self._query(parentId = str(ent['id']))
                    break

        return None


    def isdir(self, path):
        ent = self.stat(path)
        if ent is None: return False
        if ent.get('mimeType') != MimeTypes.FOLDER: return False

        return True

    
    def listdir(self, path):
        ent = self.stat(path)
        if ent is None:
            return None

        names = []
        ents = self._query(parentId = str(ent['id']))
        for ent in ents:
            names.append(ent['title'])

        return names


    def _query(self, **kwargs):
        parentId = kwargs.get("parentId")
        mimeType = kwargs.get("mimeType")

        result = []
        cached = self._gcache.get(parentId, None)
        if cached is not None:
            debug('Loading from google cache: %s' % parentId)
            result.extend(cached)
            return result

        page_token = None
        service = self._service
        query, ents = [], []
        param = {}

        if parentId is not None:
            query.append('"%s" in parents' % parentId)

        if mimeType is not None:
            query.append('mimeType = "%s"' % mimeType)

        if len(query) > 0:
            param['q'] = ' and '.join(query)

        while True:
            if page_token:
                param['pageToken'] = page_token

            files = service.files().list(**param).execute()

            ents.extend(files['items'])
            page_token = files.get('nextPageToken')

            if not page_token: break

        debug("Updating google cache: %s" % parentId)
        self._gcache[parentId] = ents

        # Normalise
        for ent in ents:
            result.append({
                'id': ent.get('id'),
                'title': ent.get('title'),
                'modifiedDate': ent.get('modifiedDate'),
                'mimeType': ent.get('mimeType')
            })

        return result
