#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

def load_tests(loader, tests, pattern):
    import os.path
    test_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "libgsync"
    )
    return loader.discover(test_dir)
