#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, os
from libgsync.output import debug
from libgsync.drive import Drive, DriveFile
from libgsync.drive.mimetypes import MimeTypes
from libgsync.sync.file import SyncFile
from apiclient.http import MediaFileUpload

if os.environ.get('DEBUG') == '1':
    debug.enable()


class TestSyncFile(unittest.TestCase):
    def test_SyncFile_relativeTo(self):
        f = SyncFile("/gsync_unittest")

        self.assertEqual(
            f.relativeTo("/gsync_unittest/open_for_read.txt"),
            "open_for_read.txt"
        )


class TestDrive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ironic, using Gsync to setup the tests, but if it fails the tests
        # will fail anyway, so we will be okay.
        assert os.path.exists("tests/data")

        drive = Drive()
        drive.delete("drive://gsync_unittest/", skipTrash=True)
        drive.mkdir("drive://gsync_unittest/")
        drive.create("drive://gsync_unittest/open_for_read.txt", {})
        drive.update("drive://gsync_unittest/open_for_read.txt", {},
            MediaFileUpload("tests/data/open_for_read.txt",
                mimetype=MimeTypes.BINARY_FILE, resumable=True
            )
        )

    def setUp(self):
        pass

    def test_Drive_normpath(self):
        drive = Drive()

        paths = [
            "drive:",
            "drive:/",
            "drive://",
            "drive://gsync_unittest",
            "drive://gsync_unittest/",
            "//gsync_unittest/a/b/c",
            "gsync_unittest/a/b/c/.",
            "/gsync_unittest/a/b/c/..",
        ]
        expected_paths = [
            "drive://",
            "drive://",
            "drive://",
            "drive://gsync_unittest",
            "drive://gsync_unittest",
            "drive://gsync_unittest/a/b/c",
            "gsync_unittest/a/b/c",
            "drive://gsync_unittest/a/b",
        ]

        for i in xrange(0, len(paths)):
            expected = str(expected_paths[i])
            actual = str(drive.normpath(paths[i]))

            self.assertEqual(expected, actual,
                "From %s expected %s but got %s" % (
                    paths[i], expected, actual
                )
            )

    def test_Drive_strippath(self):
        drive = Drive()

        paths = [
            "drive:",
            "drive:/",
            "drive://",
            "drive://gsync_unittest",
            "drive://gsync_unittest/",
            "drive://gsync_unittest/a/b/c",
            "drive://gsync_unittest/a/b/c/.",
            "drive://gsync_unittest/a/b/c/..",
        ]
        expected_paths = [
            "/",
            "/",
            "/",
            "/gsync_unittest",
            "/gsync_unittest",
            "/gsync_unittest/a/b/c",
            "/gsync_unittest/a/b/c",
            "/gsync_unittest/a/b",
        ]

        for i in xrange(0, len(paths)):
            expected = str(expected_paths[i])
            actual = str(drive.strippath(paths[i]))

            self.assertEqual(expected, actual,
                "From %s expected %s but got %s" % (
                    paths[i], expected, actual
                )
            )

    def test_Drive_pathlist(self):
        drive = Drive()
        paths = [
            "drive://",
            "drive://gsync_unittest",
            "drive://gsync_unittest/",
            "drive://gsync_unittest/a/b/c",
            "drive://gsync_unittest/a/b/c/.",
            "drive://gsync_unittest/a/b/c/..",
        ]
        expected_paths = [
            [ "drive://" ],
            [ "drive://", "gsync_unittest" ],
            [ "drive://", "gsync_unittest" ],
            [ "drive://", "gsync_unittest", "a", "b", "c" ],
            [ "drive://", "gsync_unittest", "a", "b", "c" ],
            [ "drive://", "gsync_unittest", "a", "b" ],
        ]

        for i in xrange(0, len(paths)):
            expected = str(expected_paths[i])
            actual = str(drive.pathlist(paths[i]))

            self.assertEqual(expected, actual,
                "From %s expected %s but got %s" % (
                    paths[i], expected, actual
                )
            )

    def test_DriveFile(self):
        data = {
            'id': 'fhebfhbf',
            'title': 'Test file',
            'mimeType': 'application/dummy'
        }

        f = DriveFile(**data)
        self.assertIsNotNone(f)
        self.assertEqual(f.id, data['id'])

        ff = DriveFile(**f)
        self.assertIsNotNone(ff)

    def test_isdir(self):
        drive = Drive()

        self.assertFalse(drive.isdir("drive://gsync_unittest/is_a_dir"))
        drive.mkdir("drive://gsync_unittest/is_a_dir")
        self.assertTrue(drive.isdir("drive://gsync_unittest/is_a_dir"))

        drive.create("drive://gsync_unittest/not_a_dir", {})
        self.assertFalse(drive.isdir("drive://gsync_unittest/not_a_dir"))

    def test_stat(self):
        drive = Drive()

        info = drive.stat("drive://")
        self.assertIsNotNone(info)
        self.assertEqual("root", info.id)

        info = drive.stat("drive://gsync_unittest/")
        self.assertIsNotNone(info)
        self.assertIsNotNone(info.id)
        self.assertEqual(info.title, "gsync_unittest")

    def test_mkdir(self):
        self.skipTest("slow")

        drive = Drive()
        info = drive.mkdir("drive://gsync_unittest/test_mkdir/a/b/c/d/e/f/g")
        self.assertIsNotNone(info)
        self.assertEqual(info.title, "g")

        drive.delete("drive://gsync_unittest/test_mkdir", skipTrash=True)

    def test_open_for_read(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        self.assertIsNotNone(f)

    def test_open_for_read_and_seek(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        debug("f.revisions() = %s" % repr(f.revisions()))
        debug("f._info = %s" % repr(f._info))
        self.assertNotEqual(int(f._info.fileSize), 0)
        f.seek(0, os.SEEK_END)

        self.assertNotEqual(f.tell(), 0)

    def test_open_for_read_and_read_data(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        contents = f.read()

        self.assertIsNotNone(contents)
        self.assertNotEqual(contents, "")


unittest.main()
