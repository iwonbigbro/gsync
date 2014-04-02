#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, sys


class TestGsyncOptions(unittest.TestCase):
    def setUp(self):
        self.argv = sys.argv
        sys.argv = [ "gsync", "path", "path" ]

    def tearDown(self):
        sys.argv = self.argv

    def test_01_is_initialised_on_property_inspection(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions
        GsyncListOptions = GsyncOptions.list()
        GsyncListOptionsType = libgsync.options.GsyncListOptionsType

        def hooked_init(func):
            def __hooked_init(*args, **kwargs):
                hooked_init.call_count += 1
                func(*args, **kwargs)

            return __hooked_init

        hooked_init.call_count = 0

        GsyncListOptionsType._GsyncListOptionsType__initialise_class = hooked_init(
            GsyncListOptionsType._GsyncListOptionsType__initialise_class
        )

        self.assertNotEqual(GsyncOptions.debug, None)
        self.assertNotEqual(GsyncOptions.debug, None)
        self.assertEqual(1, hooked_init.call_count)

    def test_02_list_options(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions

        self.assertFalse(isinstance(GsyncOptions.debug, list))
        self.assertTrue(isinstance(GsyncOptions.list().debug, list))
        self.assertEqual(GsyncOptions.debug, GsyncOptions.list().debug[-1])

    def test_03_dynamic_property_creation(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions

        GsyncOptions.an_undefined_attribute = "undefined_attribute"

        self.assertEqual(
            GsyncOptions.an_undefined_attribute,
            "undefined_attribute"
        )

        self.assertIsNone(GsyncOptions.another_undefined_attribute)
        self.assertEqual(
            GsyncOptions.list().another_undefined_attribute, [ None ]
        )

        self.assertEqual(
            GsyncOptions.list().another_listtype_undefined_attribute, [ None ]
        )


if __name__ == "__main__":
    unittest.main()
