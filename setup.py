#!/usr/bin/env python

# Copyright (C) 2013 Craig Phillips.  All rights reserved.

from distutils.core import setup

version = __import__('gsync.version').get_version()

setup(
    name = 'gsync',
    description = 'GSync - RSync for Google Drive',
    version = version,
    license = 'BSD License',
    author = 'Craig Phillips',
    author_email = 'iwonbigbro@gmail.com',
    url = 'https://github.com/iwonbigbro/gsync',
    packages = [
        'gsync', 
        'gsync.remote', 
        'gsync.local',
    ],
    scripts = [ 'bin/gsync.py' ],
)
