#!/usr/bin/env python

# Copyright (C) 2013 Craig Phillips.  All rights reserved.

from setuptools import setup

version = __import__('libgsync.version').get_version()

setup(
    name = 'gsync',
    description = 'GSync - RSync for Google Drive',
    version = version,
    license = 'BSD License',
    author = 'Craig Phillips',
    author_email = 'iwonbigbro@gmail.com',
    url = 'https://github.com/iwonbigbro/gsync',
    setup_requires = [
        'setuptools',
    ],
    install_requires = [
        'google-api-python-client',
        'docopt >= 0.6.0',
        'httplib2',
        'oauth2client',
        'python-dateutil',
        'urllib3',
    ],
    packages = [
        'libgsync',
        'libgsync.drive',
        'libgsync.sync',
        'libgsync.sync.file',
        'libgsync.sync.file.local',
        'libgsync.sync.file.remote',
    ],
    scripts = [
        'bin/gsync',
    ],
)
