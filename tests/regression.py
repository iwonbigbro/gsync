#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

# This differs somewhat from unittests, since unittests are testing the
# components of GSync.  This regression script uses the unittesting framework
# to run a suite of regression tests that test the entire product end-to-end.

import unittest, os

#debug.enable()

class TestRegression(unittest.TestCase):
    def setUp(self):
        pass

    def test_local_file_transfer():
        pass

unittest.main()
