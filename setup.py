#!/usr/bin/env python

# Copyright (C) 2013 Craig Phillips.  All rights reserved.

from distutils.core import setup

version = __import__('libgsync.version').get_version()

setup(
    name = 'gsync',
    description = 'GSync - RSync for Google Drive',
    version = version,
    license = 'BSD License',
    author = 'Craig Phillips',
    author_email = 'iwonbigbro@gmail.com',
    url = 'https://github.com/iwonbigbro/gsync',
    requires = [
        'docopt',
        'apiclient',
        'apiclient.discovery',
        'json',
        'oauth2client',
        'urllib3',
    ],
    packages = [
        'libgsync',
        'libgsync.drive',
        'libgsync.sync',
        'libgsync.sync.file',
    ],
    package_data = {
        'libgsync': [ 'data/*.json' ],
    },
    scripts = [ 'bin/gsync' ],
)
