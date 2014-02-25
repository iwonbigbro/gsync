#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, StringIO, sys
from libgsync.output import Channel, Debug

class TestCaseStdStringIO(unittest.TestCase):
    def setUp(self):
        self.stdout, sys.stdout = sys.stdout, StringIO.StringIO()
        self.stderr, sys.stderr = sys.stderr, StringIO.StringIO()

    def tearDown(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr


class TestChannel(TestCaseStdStringIO):
    def test_disabled_by_default(self):
        channel = Channel()
        self.assertFalse(channel.enabled())

    def test_no_output_when_disabled(self):
        channel = Channel()
        channel.disable()
        self.assertFalse(channel.enabled())

        channel("Hello World")
        self.assertEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

    def test_output_when_enabled(self):
        channel = Channel()
        channel.enable()
        self.assertTrue(channel.enabled())

        channel("Hello World")
        self.assertEqual("Hello World\n", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())


class TestDebug(TestCaseStdStringIO):
    def test_stack(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        channel.stack()

        import re
        pat = re.compile(
            r'^DEBUG: BEGIN STACK TRACE\n.*\nDEBUG: END STACK TRACE\n$',
            re.M | re.S
        )
        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())

    def test_exception_as_object(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        import re
        pat = re.compile(
            r'''^DEBUG: Exception\('Test exception',\): ''',
            re.M | re.S
        )

        try:
            raise Exception("Test exception")
        except Exception, e:
            channel.exception(e)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())

    def test_exception_as_string(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        import re
        pat = re.compile(
            r'''^DEBUG: 'Test exception': ''',
            re.M | re.S
        )

        try:
            raise Exception("Test exception")
        except Exception, e:
            channel.exception(str(e))

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())
        
    def test_exception_as_custom_string(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        custom_string = "This is a custom string"

        import re
        pat = re.compile(
            r'''^DEBUG: %s: ''' % repr(custom_string),
            re.M | re.S
        )

        try:
            raise Exception("Test exception")
        except Exception, e:
            channel.exception(custom_string)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())

    def test_exception_as_default(self):
        channel = Debug()
        channel.enable()
        self.assertTrue(channel.enabled())

        import re
        pat = re.compile(
            r'''^DEBUG: 'Exception': ''',
            re.M | re.S
        )

        try:
            raise Exception("Test exception")
        except Exception, e:
            channel.exception()

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))
        self.assertEqual("", sys.stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
