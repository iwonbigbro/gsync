# Copyright (C) 2013 Craig Phillips.  All rights reserved.

from oauth2client.client import OAuth2Credentials
import os, sys
from libgsync.verbose import verbose

class ENoTTY(Exception):
    pass

class EGetAuthURL(Exception):
    pass

class EExchange(Exception):
    pass

class EFileNotFound(Exception):
    def __init__(self, filename):
        self.msg = "File not found: %s" % msg

class MimeTypes():
    FOLDER = "application/vnd.google-apps.folder"

class Drive():
    _credentials = None
    _service = None
    _storage = None
    _cache = {}

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


    def find(self, path):
        dirname, filename = os.path.split(path)
        files = self.list(str(dirname))

        verbose("Searching for: %s" % path)

        for f in files:
            verbose("Checking: %s" % f['title'])

            if f['title'] == filename:
                verbose("Found: %s" % path)
                return f
        
        return None


    def list(self, path = None, recursive = False):
        if path is None:
            path = '/'
        elif not isinstance(path, str):
            raise TypeError("path")
        elif path[0] != '/':
            raise EFileNotFound(path)

        # Break down the path and enumerate each folder
        paths = []
        while True:
            path, folder = os.path.split(path)

            if folder != "":
                paths.append(folder)
            elif path != "":
                paths.append(folder)
                break

        havePath = (len(paths) > 0)
        if havePath:
            mimeType = MimeTypes.FOLDER
        else:
            mimeType = None

        ents = self._list('root', mimeType)
        if len(ents) == 0:
            raise EFileNotFound(path)

        if not havePath:
            return ents

        last = False
        while not last:
            d = paths.pop()
            last = (len(paths) == 0)

            if last: mimeType = None

            for ent in ents:
                if d == ent['title']:
                    ents = self._list(str(ent['id']), mimeType)
                    break

        if recursive:
            def _populate(ents):
                for ent in ents:
                    if ent['mimeType'] == MimeTypes.FOLDER:
                        children = self._list(str(ent['id']), None)
                        ent['children'] = children
                        _populate(children)

            _populate(ents)

        return ents

                
    def _list(self, parentId, mimeType):
        result = []

        cached = self._cache.get(parentId, None)
        if cached is not None:
            verbose('Result already cached: %s' % parentId)
            result.extend(cached)
            return result

        page_token = None
        service = self._service
        query = [] 
        param = {}
        ents = []

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

        self._cache[parentId] = ents

        # Normalise
        for ent in ents:
            result.append({
                'id': ent.get('id'),
                'title': ent.get('title'),
                'modifiedDate': ent.get('modifiedDate'),
                'mimeType': ent.get('mimeType')
            })

        return result
