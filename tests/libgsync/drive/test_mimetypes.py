#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest
from libgsync.drive.mimetypes import MimeTypes

class TestDriveMimeTypes(unittest.TestCase):
    def setUp(self):
        try:
            import magic
            self.magic_from_file = magic.from_file
        except Exception:
            pass

    def tearDown(self):
        try:
            import magic
            magic.from_file = self.magic_from_file
        except Exception:
            pass

    def test_DriveMimeTypes_get_unknown_mimetype(self):
        self.assertEqual(MimeTypes.get("/dev/null"), "inode/chardevice")

    def test_DriveMimeTypes_get_binary_mimetype(self):
        self.assertEqual(
            MimeTypes.get("/bin/true"), "application/x-executable"
        )

    def test_DriveMimeTypes_get_folder_mimetype(self):
        self.assertEqual(MimeTypes.get("/bin"), "inode/directory")

    def test_DriveMimeTypes_get_magic_exception(self):
        try:
            import magic
        except Exception:
            self.skipTest("Module 'magic' not present")
            return

        def func(*args, **kwargs):
            raise Exception("Fake exception")

        magic.from_file = func

        self.assertEqual(MimeTypes.get("/bin/true"), MimeTypes.NONE)


if __name__ == "__main__":
    unittest.main()
