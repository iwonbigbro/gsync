#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest
from libgsync.drive.file import DriveFile


class TestCaseDriveFile(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    
    def test_drive_file_is_a_dict(self):
        self.assertTrue(isinstance(DriveFile(), dict))


    def test_instantiate_from_dictionary(self):
        data = {
            'a': 'a_val',
            'b': 'b_val'
        }

        drive_file = DriveFile(data)

        self.assertEqual(data['a'], drive_file.a)
        self.assertEqual(data['b'], drive_file.b)


if __name__ == "__main__":
    unittest.main()
