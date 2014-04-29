#!/usr/bin/env python
# -*- coding: utf8 -*-
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Defines output channels for gsync"""

import os, sys, inspect, re, codecs
from datetime import datetime

# Make stdout unbuffered.
sys.stdout = (codecs.getwriter(sys.stdout.encoding))\
    (os.fdopen(sys.stdout.fileno(), "w", 0), "replace")


class Channel(object):
    """Base channel class to define the interface"""

    _priority = -1 

    def enable(self):
        """Enables the channel."""

        if self._priority < 0:
            self._priority = 0
        self._priority += 1

    def disable(self): 
        """Disables the channel."""

        self._priority = -1

    def enabled(self):
        """Returns True if the channel is enabled."""

        return self._priority > 0

    def __call__(self, msg, priority=1):
        self.write(msg, priority)

    def write(self, msg, priority=1):
        """Writes messages to the buffer provided by this channel."""

        if self._priority >= priority:
            sys.stdout.write(u"%s\n" % unicode(msg))

class Debug(Channel):
    """
    Defines a debug channel for writing debugging information to stdout
    and stderr.
    """
    def write(self, msg, priority=1):
        if self._priority >= priority:
            stack = inspect.stack()
            indent = "".join([ " " for _ in range(len(stack) - 2) ])

            self._write_frame(stack[2], msg, indent)

    def _write_frame(self, frame, message=None, indent=""):
        """Writes a formatted stack frame to the channel buffer."""

        filename, lineno, function = frame[1:4]
        filename = re.sub(r'^.*libgsync/', "", filename)
        filename = re.sub(r'/__init__.py', "/", filename)
        if message is not None:
            super(Debug, self).write("DEBUG: %s%s:%d:%s(): %s" % (
                indent, filename, lineno, function, message
            ))
        else:
            super(Debug, self).write("DEBUG: %s%s:%d:%s()" % (
                indent, filename, lineno, function
            ))

    def stack(self):
        """Writes a stack trace to the channel buffer."""

        super(Debug, self).write("DEBUG: BEGIN STACK TRACE")

        stack = inspect.stack()[1:]
        for frame in stack:
            self._write_frame(frame, indent="    ")

        super(Debug, self).write("DEBUG: END STACK TRACE")

    def exception(self, ex = "Exception"):
        """Writes a formatted exception to the channel buffer."""

        if isinstance(ex, Exception):
            super(Debug, self).write("DEBUG: %s: %s" % (
                repr(ex), str(ex)
            ), -1)

        import traceback
        super(Debug, self).write("DEBUG: %s: %s" % (
            repr(ex), "".join(traceback.format_tb(sys.exc_info()[2]))
        ), -1)

    def function(self, func):
        """Provides function decoration debugging"""

        if self._priority < 1:
            return func

        def __function(*args, **kwargs):
            ret = func(*args, **kwargs)
            self.write("%s(%s, %s) = %s" % (
                func.__name__, repr(args), repr(kwargs), repr(ret)
            ))
            return ret

        return __function


class Verbose(Channel):
    """
    Defines a channel for writing verbose output to stdout and stderr.
    """
    pass


class Itemize(object):
    """
    Defines a channel for the output of the rsync style itemized change
    summary on stdout and stderr.
    """
    def __call__(self, changes, filename):
        sys.stdout.write(u"%11s %s\n" % \
            (unicode(changes[:11]), unicode(filename)))


class Progress(object):
    """
    Defines a non-singleton channel for writing file transfer progress
    output to stdout and stderr.
    """
    def __init__(self, enable_output = True, callback = None):
        self._callback = callback
        self._enable_output = enable_output
        self._start = datetime.now()

        self.bytes_written = 0L
        self.bytes_total = 0L
        self.percentage = 0
        self.time_taken = 0

        self.write()

    def write(self):
        """
        Writes the current state of the transfer to the output stream.
        """
        if self._enable_output:
            epoch = int(self.time_taken)
            secs = epoch % 60
            mins = int(epoch / 60) % 60
            hrs = int((epoch / 60) / 60) % 60

            sys.stdout.write(u"\r%12d %3d%% %11s %10s" % (
                self.bytes_written, self.percentage, unicode(self.rate()),
                u"%d:%02d:%02d" % (hrs, mins, secs)
            ))
        
    def __call__(self, status):
        self.time_taken = (datetime.now() - self._start).seconds
        self.bytes_written = long(status.resumable_progress)
        self.percentage = int(status.progress() * 100.0)
        self.bytes_total = status.total_size

        self.write()

        if self._callback is not None:
            self._callback(status)

    def rate(self):
        """
        Returns a string representing the bytes transferred against time
        taken, as a rate of units of bytes per second.
        """
        rate = float(self.bytes_written) / max(0.1, float(self.time_taken))

        for modifier in [ 'B', 'KB', 'MB', 'GB', 'TB' ]:
            if rate < 1024.0:
                return "%3.2f%s/s" % (rate, modifier)
            rate /= 1024.0

    def complete(self, bytes_written):
        """
        Called when a transfer has been completed, so that the summary can
        be flushed for this transfer.
        """
        self.time_taken = (datetime.now() - self._start).seconds
        self.bytes_written = bytes_written

        if self.bytes_total > 0L:
            self.percentage = int(
                (float(self.bytes_written) / float(self.bytes_total)) * 100.0
            )
        elif self.bytes_written == 0L:
            self.percentage = 100
        else:
            self.percentage = 0

        if self._enable_output:
            self.write()
            sys.stdout.write(u"\n")


class Critical(object):
    """
    Defines a channel for critical messages to be written to stdout
    and stderr IO buffers.
    """
    def __call__(self, ex):
        sys.stderr.write(u"gsync: %s\n" % unicode(ex))

        from libgsync import __version__
        import traceback

        tb = traceback.extract_tb((sys.exc_info())[-1])
        source_file = "unknown"
        lineno = 0

        for i in xrange(len(tb) - 1, -1, -1):
            if re.match(r'^.*/libgsync/.*$', tb[i][0]) is not None:
                source_file = os.path.basename(tb[i][0])
                if source_file == "__init__.py":
                    source_file = os.path.basename(
                        os.path.dirname(tb[i][0])
                    )
                lineno = tb[i][1]
                break

        sys.stderr.write(u"gsync error: %s at %s(%d) [client=%s]\n" % (
            ex.__class__.__name__, source_file, lineno, __version__
        ))


verbose = Verbose() # pylint: disable-msg=C0103
debug = Debug() # pylint: disable-msg=C0103
itemize = Itemize() # pylint: disable-msg=C0103
critical = Critical() # pylint: disable-msg=C0103

__all__ = [ "verbose", "debug", "itemize", "critical" ]

if os.environ.get('GSYNC_DEBUG', '0') == '1': # pragma: no cover
    debug.enable()
