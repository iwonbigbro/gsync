#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, tempfile, sys, os, shutil, hashlib
from libgsync.sync import Sync

try: import posix as os_platform
except ImportError: import nt as os_platform

def sha256sum(path):
    blocksize = 65536
    sha = hashlib.md5()
    with open(path, "r+b") as f:
        for block in iter(lambda: f.read(blocksize), ""):
            sha.update(block)

    return sha.hexdigest()


class TestCaseSync(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.argv = sys.argv

    def tearDown(self):
        sys.argv = self.argv
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

    def test_local_files(self):
        src = os.path.join("tests", "data")
        dst = self.tempdir

        sys.argc = 3
        sys.argv = [ "gsync", src, dst ]

        sync = Sync(src, dst)

        self.assertFalse(os.path.exists(
            os.path.join(self.tempdir, "open_for_read.txt")
        ))

        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(
            os.path.join(self.tempdir, "open_for_read.txt")
        ))

        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(os.path.join(self.tempdir, "open_for_read.txt"))
        )

    def test_local_files_force_dest_file(self):
        src = os.path.join("tests", "data")
        dst = os.path.join(self.tempdir, "a_different_filename.txt")

        sys.argc = 3
        sys.argv = [ "gsync", src, dst ]

        import libgsync.options
        libgsync.options.GsyncOptions.force_dest_file = True

        sync = Sync(src, dst)

        self.assertFalse(os.path.exists(dst))

        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))

        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(dst)
        )

    def test_non_existent_source_file(self):
        src = os.path.join("tests", "data")
        dst = self.tempdir

        sys.argc = 3
        sys.argv = [ "gsync", src, dst ]

        sync = Sync(src, dst)

        self.assertFalse(os.path.exists(
            os.path.join(self.tempdir, "open_for_read.txt")
        ))

        sync("file_not_found.txt")

        self.assertFalse(os.path.exists(
            os.path.join(self.tempdir, "file_not_found.txt")
        ))


if __name__ == "__main__":
    unittest.main()
