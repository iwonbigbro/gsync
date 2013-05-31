#!/usr/bin/env python

import unittest, os
from libgsync.output import debug
from libgsync.drive import Drive
from libgsync.drive import DriveFile
from libgsync.config import Data

#debug.enable()

class TestConfigData(unittest.TestCase):
    def test_DataSaveAndLoad(self):
        path = "/tmp/config_data_test"

        d = Data(path)
        d.set({ 'a': 1, 'b': 2 })
        d.save()

        o = d.load()

        self.assertEqual(o['a'], 1)
        self.assertEqual(o['b'], 2)

    def test_DataSaveAndLoad_JSONEncoder(self):
        path = "/tmp/config_data_test"

        d = Data(path, encoder="json")
        d.set({ 'a': 1, 'b': 2 })
        d.save()

        o = d.load()

        self.assertEqual(o['a'], 1)
        self.assertEqual(o['b'], 2)


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

    def test_open_for_read(self):
        drive = Drive()
        f = drive.open("/unittest/open_for_read.txt", "r")
        self.assertIsNotNone(f)

    def test_open_for_read_and_seek(self):
        drive = Drive()
        f = drive.open("/unittest/open_for_read.txt", "r")
        f.seek(0, os.SEEK_END)

        self.assertNotEqual(f.tell(), 0)


unittest.main()
