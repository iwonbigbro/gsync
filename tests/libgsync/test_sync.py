#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, tempfile, sys, os, shutil, hashlib
from libgsync.sync import Sync
from libgsync.options import GsyncOptions

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

        # Setup fake arguments to satisfy GsyncOptions and docopt validation.
        sys.argv = [ "gsync", os.path.join("tests", "data"), self.tempdir ]
        sys.argc = len(sys.argv)

        # Reset this flag for tests that do not expect it.
        GsyncOptions.force_dest_file = None

    def tearDown(self):
        sys.argv = self.argv
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

    def test_local_files(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "open_for_read.txt")

        self.assertFalse(os.path.exists(dst))

        sync = Sync(src, self.tempdir)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))
        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(dst)
        )

    def test_local_files_with_identical_mimetypes(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "open_for_read.txt")

        # Copy a binary file to ensure it isn't ascii.
        shutil.copyfile(os.path.join(src, "open_for_read.txt"), dst)
        self.assertTrue(os.path.exists(dst))

        sync = Sync(src, self.tempdir)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))
        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(os.path.join(self.tempdir, "open_for_read.txt"))
        )

    def test_local_files_with_different_mimetypes(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "open_for_read.txt")

        # Copy a binary file to ensure it isn't ascii.
        shutil.copyfile("/bin/true", dst)
        self.assertTrue(os.path.exists(dst))

        sync = Sync(src, self.tempdir)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))
        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(os.path.join(self.tempdir, "open_for_read.txt"))
        )

    def test_local_files_force_dest_file(self):
        src = sys.argv[1]
        dst = os.path.join(self.tempdir, "a_different_filename.txt")

        GsyncOptions.force_dest_file = True

        self.assertFalse(os.path.exists(dst))

        sync = Sync(src, dst)
        sync("open_for_read.txt")

        self.assertTrue(os.path.exists(dst))

        self.assertEqual(
            sha256sum(os.path.join(src, "open_for_read.txt")),
            sha256sum(dst)
        )

    def test_non_existent_source_file(self):
        dst = os.path.join(self.tempdir, "a_different_filename.txt")

        self.assertFalse(os.path.exists(dst))

        sync = Sync(sys.argv[1], dst)
        sync("file_not_found.txt")

        self.assertFalse(os.path.exists(dst))


if __name__ == "__main__":
    unittest.main()
