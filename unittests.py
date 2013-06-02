#!/usr/bin/env python

import unittest, os
from libgsync.output import debug
from libgsync.drive import Drive, DriveFile
from libgsync.sync.file import SyncFile

#debug.enable()

class TestSyncFile(unittest.TestCase):
    def test_SyncFile_relativeTo(self):
        f = SyncFile("/unittest")

        self.assertEqual(
            f.relativeTo("/unittest/open_for_read.txt"),
            "open_for_read.txt"
        )

class TestDrive(unittest.TestCase):
    def setUp(self):
        pass

    def test_Drive_normpath(self):
        drive = Drive()

        paths = [
            "drive:",
            "drive:/",
            "drive://",
            "drive://unittest",
            "drive://unittest/",
            "//unittest/a/b/c",
            "unittest/a/b/c/.",
            "/unittest/a/b/c/..",
        ]
        expected_paths = [
            "drive://",
            "drive://",
            "drive://",
            "drive://unittest",
            "drive://unittest",
            "drive://unittest/a/b/c",
            "unittest/a/b/c",
            "drive://unittest/a/b",
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
            "drive://unittest",
            "drive://unittest/",
            "drive://unittest/a/b/c",
            "drive://unittest/a/b/c/.",
            "drive://unittest/a/b/c/..",
        ]
        expected_paths = [
            "/",
            "/",
            "/",
            "/unittest",
            "/unittest",
            "/unittest/a/b/c",
            "/unittest/a/b/c",
            "/unittest/a/b",
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
            "drive://unittest",
            "drive://unittest/",
            "drive://unittest/a/b/c",
            "drive://unittest/a/b/c/.",
            "drive://unittest/a/b/c/..",
        ]
        expected_paths = [
            [ "drive://" ],
            [ "drive://", "unittest" ],
            [ "drive://", "unittest" ],
            [ "drive://", "unittest", "a", "b", "c" ],
            [ "drive://", "unittest", "a", "b", "c" ],
            [ "drive://", "unittest", "a", "b" ],
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

        self.assertTrue(drive.isdir("drive://unittest/"))
        self.assertFalse(drive.isdir("drive://unittest/open_for_read.txt"))

    def test_stat(self):
        drive = Drive()

        info = drive.stat("drive://")
        self.assertIsNotNone(info)
        self.assertEqual("root", info.id)

        info = drive.stat("drive://unittest/")
        self.assertIsNotNone(info)
        self.assertIsNotNone(info.id)
        self.assertEqual(info.title, "unittest")

    def test_mkdir(self):
        self.skipTest("slow")

        drive = Drive()
        info = drive.mkdir("drive://unittest/test_mkdir/a/b/c/d/e/f/g")
        self.assertIsNotNone(info)
        self.assertEqual(info.title, "g")

        drive.rm("drive://unittest/test_mkdir", recursive=True)

    def test_open_for_read(self):
        drive = Drive()
        f = drive.open("drive://unittest/open_for_read.txt", "r")
        self.assertIsNotNone(f)

    def test_open_for_read_and_seek(self):
        drive = Drive()
        f = drive.open("drive://unittest/open_for_read.txt", "r")
        f.seek(0, os.SEEK_END)

        self.assertNotEqual(f.tell(), 0)

    def test_open_for_read_and_read_data(self):
        drive = Drive()
        f = drive.open("drive://unittest/open_for_read.txt", "r")
        contents = f.read()

        self.assertIsNotNone(contents)
        self.assertNotEqual(contents, "")


unittest.main()
