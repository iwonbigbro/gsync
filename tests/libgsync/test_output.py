#!/usr/bin/env python

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

import unittest, StringIO, sys
from libgsync.output import Channel, Debug, Itemize, Progress

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


class TestItemize(TestCaseStdStringIO):
    def test_callable(self):
        channel = Itemize()

        channel(">+", "/dev/null")

        self.assertEqual(sys.stdout.getvalue(), "         >+ /dev/null\n")
        self.assertEqual("", sys.stderr.getvalue())

        sys.stdout.truncate(0)

        channel(">+++++++++++++++++", "/dev/null")

        self.assertEqual(sys.stdout.getvalue(), ">++++++++++ /dev/null\n")
        self.assertEqual("", sys.stderr.getvalue())


class ProgressStatus(object):
    def __init__(self, total_size = 0, resumable_progress = 0):
        self.total_size = total_size
        self.resumable_progress = resumable_progress

    def progress(self):
        return float(self.resumable_progress) / float(self.total_size)


class TestProgress(TestCaseStdStringIO):
    def test_with_disabled_output(self):
        channel = Progress(enableOutput = False)

        self.assertEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

    def test_enabled_output_by_default(self):
        channel = Progress()

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

    def test_with_enabled_output(self):
        channel = Progress(enableOutput = True)

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

    def test_status_messages_with_callback(self):
        def callback(status):
            callback.called = True

        callback.called = False

        channel = Progress(callback=callback)

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

        import re

        for i in ( 5, 10, 20, 40, 50, 75, 100 ):
            pat = re.compile(
                r'^\s+%d\s+%d%%\s+\d+\.\d{2}(?:B|KB|MB|GB|TB)/s\s+\d+:\d+:\d+$' % (i, i),
                re.S | re.M
            )

            sys.stdout.truncate(0)
            channel(ProgressStatus(100, i))

            self.assertIsNotNone(pat.search(sys.stdout.getvalue()))

        self.assertTrue(callback.called)

    def test_rate_normalization(self):
        channel = Progress()

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

        fileSize = 1000000000

        import re
        pat = re.compile(
            r'^\s+%d\s+%d%%\s+\d+\.\d{2}(?:KB|MB|GB|TB)/s\s+\d+:\d+:\d+$' % (fileSize, 100),
            re.S | re.M
        )

        sys.stdout.truncate(0)
        channel(ProgressStatus(fileSize, fileSize / 4))

        self.assertIsNone(pat.search(sys.stdout.getvalue()))

        sys.stdout.truncate(0)
        channel.complete(fileSize)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))

    def test_zero_byte_file(self):
        channel = Progress()

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

        import re
        pat = re.compile(
            r'^\s+%d\s+%d%%\s+\d+\.\d{2}(?:B|KB|MB|GB|TB)/s\s+\d+:\d+:\d+$' % (0, 100),
            re.S | re.M
        )

        sys.stdout.truncate(0)
        channel.complete(0)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))


    def test_complete(self):
        channel = Progress()

        self.assertNotEqual("", sys.stdout.getvalue())
        self.assertEqual("", sys.stderr.getvalue())

        import re
        pat = re.compile(
            r'^\s+%d\s+%d%%\s+\d+\.\d{2}(?:B|KB|MB|GB|TB)/s\s+\d+:\d+:\d+$' % (100, 100),
            re.S | re.M
        )

        sys.stdout.truncate(0)
        channel(ProgressStatus(100, 25))

        self.assertIsNone(pat.search(sys.stdout.getvalue()))

        sys.stdout.truncate(0)
        channel.complete(100)

        self.assertIsNotNone(pat.search(sys.stdout.getvalue()))


if __name__ == "__main__":
    unittest.main()
