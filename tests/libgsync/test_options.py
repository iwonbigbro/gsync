#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, sys


class TestGsyncOptions(unittest.TestCase):
    def setUp(self):
        self.argv = sys.argv
        sys.argv = [ "gsync", "path", "path" ]

    def tearDown(self):
        sys.argv = self.argv

    def test_00_GsyncOptions_is_the_only_object_in_the_module(self):
        import libgsync.options
        found = []
        expected = [ "GsyncOptions" ]

        for k in libgsync.options.__dict__.iterkeys():
            if k.startswith("__"): continue
            found.append(k)

        self.assertEqual(found, expected)

    def test_01_GsyncOptions_is_initialised_on_property_inspection(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions
        GsyncOptionsType = object.__getattribute__(
            GsyncOptions, "__metaclass__"
        )

        initClass = GsyncOptionsType._GsyncOptionsType__initialiseClass
        def myInitClass(*args, **kwargs):
            myInitClass.call_count += 1
            initClass(*args, **kwargs)

        myInitClass.call_count = 0
        GsyncOptionsType._GsyncOptionsType__initialiseClass = myInitClass

        self.assertNotEqual(GsyncOptions.debug, None)
        self.assertNotEqual(GsyncOptions.debug, None)
        self.assertEqual(1, myInitClass.call_count)

    def test_02_GsyncOptions_list_options(self):
        import libgsync.options
        GsyncOptions = libgsync.options.GsyncOptions

        self.assertFalse(isinstance(GsyncOptions.debug, list))
        self.assertTrue(isinstance(GsyncOptions.list().debug, list))
        self.assertEqual(GsyncOptions.debug, GsyncOptions.list().debug[-1])
