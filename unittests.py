#!/usr/bin/env python

import unittest
from libgsync.output import debug
from libgsync.drive import Drive
from libgsync.drive import DriveFile

debug.enable()

class TestDrive(unittest.TestCase):
    def setUp(self):
        pass

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

    def test_stat(self):
        drive = Drive()
        info = drive.stat("/")
        self.assertIsNotNone(info)
        self.assertEqual("root", info.id)

    def test_mkdir(self):
        drive = Drive()
        info = drive.mkdir("/unittest/test_mkdir/a/b/c/d/e/f/g")
        self.assertIsNotNone(info)
        self.assertEqual(info.title, "g")

        drive.rm("/unittest/test_mkdir", recursive=True)

    def test_open_for_write(self):
        drive = Drive()
        f = drive.open("/unittest/open_for_write.bin", "w")
        self.assertIsNotNone(f)

        f.write("This is some data for the file")

        self.assertNotEqual(f.tell(), 0)


unittest.main()
