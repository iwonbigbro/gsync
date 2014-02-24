#!/usr/bin/env python

# Copyright (C) 2013 Craig Phillips.  All rights reserved.

from datetime import datetime
from setuptools import setup
from libgsync import __version__

delim = """
=============================================================================

"""

setup(
    name = 'gsync',
    description = 'GSync - RSync for Google Drive',
    version = __version__,
    license = 'BSD License',
    author = 'Craig Phillips',
    author_email = 'iwonbigbro@gmail.com',
    keywords = 'rsync gsync google-drive transfer copy files ftp',
    url = 'https://github.com/iwonbigbro/gsync',
    long_description = delim.join([
        "Gsync %s - %s" % (__version__, str(datetime.utcnow())),
        open("README.rst").read(),
        "Change history",
        open("CHANGELIST.rst").read()
    ]),
    test_suite = "tests",
    setup_requires = [
        'setuptools',
    ],
    install_requires = [
        'google-api-python-client >= 1.2',
        'docopt >= 0.6.0',
        'httplib2 >= 0.8',
        'oauth2client >= 1.1',
        'python-dateutil >= 1.5',
        'python-magic >= 0.4.6',
        'urllib3 >= 1.5',
    ],
    packages = [
        'libgsync',
        'libgsync.drive',
        'libgsync.options',
        'libgsync.sync',
        'libgsync.sync.file',
        'libgsync.sync.file.local',
        'libgsync.sync.file.remote',
    ],
    scripts = [
        'bin/gsync',
    ],
)
