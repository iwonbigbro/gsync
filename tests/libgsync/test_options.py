#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, sys


class TestGsyncOptions(unittest.TestCase):
    def setUp(self):
        self.argv = sys.argv
        sys.argv = [ "gsync", "path", "path" ]

    def tearDown(self):
        sys.argv = self.argv

    def test_00_is_the_only_object_in_the_module(self):
        import libgsync.options
        found = []
        expected = [ "GsyncOptions" ]

        for k in libgsync.options.__dict__.iterkeys():
            if k.startswith("__"): continue
            found.append(k)

        self.assertEqual(found, expected)

    def test_01_is_initialised_on_property_inspection(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions
        GsyncListOptions = GsyncOptions.list()
        GsyncListOptionsType = object.__getattribute__(
            GsyncListOptions, "__metaclass__"
        )

        init = GsyncListOptionsType._GsyncListOptionsType__initialiseClass
        def hookedInit(*args, **kwargs):
            hookedInit.call_count += 1
            init(*args, **kwargs)

        hookedInit.call_count = 0
        GsyncListOptionsType._GsyncListOptionsType__initialiseClass = hookedInit

        self.assertNotEqual(GsyncOptions.debug, None)
        self.assertNotEqual(GsyncOptions.debug, None)
        self.assertEqual(1, hookedInit.call_count)

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
