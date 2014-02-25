#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.
import unittest, os, inspect
from libgsync.output import debug
from libgsync.drive import Drive, DriveFile, DrivePathCache
from libgsync.drive.mimetypes import MimeTypes
from apiclient.http import MediaFileUpload

# This decorator is used to skip tests that require authentication and a
# connection to a user's drive account.  Rather than fail setup or tests,
# we simply skip them and flag them as such.
def requires_auth(func):
    def __requires_auth(testcase, *args, **kwargs):
        config_dir = Drive()._getConfigDir()
        credentials = os.path.join(config_dir, "credentials")

        if os.path.exists(credentials):
            return func(testcase, *args, **kwargs)

        if inspect.isclass(testcase):
            return None

        testcase.skipTest("Authentication not established")
        return None

    return __requires_auth

@requires_auth
def setup_drive_data(testcase):
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


class TestDrivePathCache(unittest.TestCase):
    def test_constructor(self):
        dpc = DrivePathCache({
            "junk": "junk",
            "drive://gsync_unittest/a_valid_path": {}
        })

        self.assertEqual(dpc.get("junk"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/a_valid_path"), {})

    def test_put(self):
        dpc = DrivePathCache()

        self.assertEqual(dpc.get("drive://gsync_unittest"), None)
        dpc.put("drive://gsync_unittest//////", {})
        self.assertEqual(dpc.get("drive://gsync_unittest"), {})

    def test_get(self):
        dpc = DrivePathCache()

        dpc.put("drive://gsync_unittest", {})
        self.assertEqual(dpc.get("drive://gsync_unittest/123"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest//////"), {})
        self.assertEqual(dpc.get("drive://gsync_unittest"), {})

    def test_clear(self):
        dpc = DrivePathCache()

        dpc.put("drive://gsync_unittest/1", {})
        dpc.put("drive://gsync_unittest/2", {})
        dpc.put("drive://gsync_unittest/3", {})

        self.assertEqual(dpc.get("drive://gsync_unittest/1"), {})
        self.assertEqual(dpc.get("drive://gsync_unittest/2"), {})
        self.assertEqual(dpc.get("drive://gsync_unittest/3"), {})

        dpc.clear("drive://gsync_unittest/1")
        self.assertEqual(dpc.get("drive://gsync_unittest/1"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/2"), {})
        self.assertEqual(dpc.get("drive://gsync_unittest/3"), {})

        dpc.clear("drive://gsync_unittest/2")
        self.assertEqual(dpc.get("drive://gsync_unittest/1"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/2"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/3"), {})

        dpc.clear("drive://gsync_unittest/3")
        self.assertEqual(dpc.get("drive://gsync_unittest/1"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/2"), None)
        self.assertEqual(dpc.get("drive://gsync_unittest/3"), None)

    def test_repr(self):
        dpc = DrivePathCache()
        self.assertEqual(repr(dpc), "DrivePathCache({})")


class TestDrive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_drive_data(cls)

    def test_normpath(self):
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

    def test_strippath(self):
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

    def test_pathlist(self):
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

    @requires_auth
    def test_isdir(self):
        drive = Drive()

        self.assertFalse(drive.isdir("drive://gsync_unittest/is_a_dir"))
        drive.mkdir("drive://gsync_unittest/is_a_dir")
        self.assertTrue(drive.isdir("drive://gsync_unittest/is_a_dir"))

        drive.create("drive://gsync_unittest/not_a_dir", {})
        self.assertFalse(drive.isdir("drive://gsync_unittest/not_a_dir"))

    @requires_auth
    def test_stat(self):
        drive = Drive()

        info = drive.stat("drive://")
        self.assertIsNotNone(info)
        self.assertEqual("root", info.id)

        info = drive.stat("drive://gsync_unittest/")
        self.assertIsNotNone(info)
        self.assertIsNotNone(info.id)
        self.assertEqual(info.title, "gsync_unittest")

    @requires_auth
    def test_mkdir(self):
        drive = Drive()

        info = drive.mkdir("drive://gsync_unittest/test_mkdir/a/b/c/d/e/f/g")
        self.assertIsNotNone(info)
        self.assertEqual(info.title, "g")

        drive.delete("drive://gsync_unittest/test_mkdir", skipTrash=True)

    @requires_auth
    def test_listdir(self):
        drive = Drive()

        info = drive.create("drive://gsync_unittest/a_file_to_list", {})
        self.assertIsNotNone(info)

        items = drive.listdir("drive://gsync_unittest/")
        self.assertTrue(isinstance(items, list))
        self.assertTrue("a_file_to_list" in items)

    @requires_auth
    def test_create(self):
        drive = Drive()

        info = drive.create("drive://gsync_unittest/create_test", {
            "title": "Will be overwritten",
            "description": "Will be kept"
        })
        self.assertEqual(info['title'], "create_test")
        self.assertEqual(info['description'], "Will be kept")

        info2 = drive.create("drive://gsync_unittest/create_test", {
            "description": "This file will replace the first one"
        })
        self.assertNotEqual(info['id'], info2['id'])
        self.assertEqual(info2['title'], "create_test")
        self.assertEqual(info2['description'], "This file will replace the first one")

    @requires_auth
    def test_update_with_progress(self):
        drive = Drive()

        info = drive.create("drive://gsync_unittest/update_test", {
            "description": "Old description"
        })
        self.assertEqual(info['title'], "update_test")

        def progress_callback(status):
            progress_callback.called = True

        progress_callback.called = False

        info = drive.update("drive://gsync_unittest/update_test", {
                "description": "New description"
            },
            MediaFileUpload("tests/data/open_for_read.txt",
                mimetype=MimeTypes.BINARY_FILE, resumable=True
            ),
            progress_callback
        )
        self.assertEqual(info['description'], "New description")
        self.assertTrue(int(info['fileSize']) > 0)
        self.assertTrue(progress_callback.called)


class TestDriveFileObject(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup_drive_data(cls)

    def test_constructor(self):
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
        self.assertEqual(f.id, ff.id)

    @requires_auth
    def test_open_for_read(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        self.assertIsNotNone(f)

    @requires_auth
    def test_open_for_read_and_seek(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")

        self.assertNotEqual(int(f._info.fileSize), 0)
        f.seek(0, os.SEEK_END)

        self.assertNotEqual(f.tell(), 0)

    @requires_auth
    def test_open_for_read_and_read_data(self):
        drive = Drive()
        f = drive.open("drive://gsync_unittest/open_for_read.txt", "r")
        contents = f.read()

        self.assertIsNotNone(contents)
        self.assertNotEqual(contents, "")

    @requires_auth
    def test_revisions(self):
        drive = Drive()

        num_revisions = 6

        info = drive.create("drive://gsync_unittest/revision_test", {
            "description": "revision-0"
        })
        self.assertEqual(info['description'], "revision-0")

        for revision in range(1, num_revisions):
            description = "revision-%d" % revision
            info = drive.update("drive://gsync_unittest/revision_test", {
                    "description": description
                },
                MediaFileUpload("tests/data/open_for_read.txt",
                    mimetype=MimeTypes.BINARY_FILE, resumable=True
                )
            )
            self.assertEqual(info['description'], description)

        f = drive.open("drive://gsync_unittest/revision_test", "r")
        revisions = f.revisions()

        self.assertEqual(len(revisions), num_revisions)
        self.assertEqual(int(revisions[0]['fileSize']), 0)
        self.assertNotEqual(int(revisions[-1]['fileSize']), 0)


if __name__ == "__main__":
    unittest.main()
