#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest
from libgsync.drive.mimetypes import MimeTypes

class TestDriveMimeTypes(unittest.TestCase):
    def setUp(self):
        pass

    def test_DriveMimeTypes_get_unknown_mimetype(self):
        self.assertEqual(MimeTypes.get("/dev/null"), "inode/chardevice")

    def test_DriveMimeTypes_get_binary_mimetype(self):
        self.assertEqual(
            MimeTypes.get("/bin/true"), "application/x-executable"
        )

    def test_DriveMimeTypes_get_folder_mimetype(self):
        self.assertEqual(MimeTypes.get("/bin"), "inode/directory")

if __name__ == "__main__":
    unittest.main()
