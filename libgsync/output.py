# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import os, sys, inspect, re
from datetime import datetime

# Make stdout unbuffered.
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

class Channel(object):
    _priority = -1 

    def enable(self):
        if self._priority < 0:
            self._priority = 0
        self._priority += 1

    def disable(self):
        self._priority = -1

    def enabled(self):
        return self._priority > 0

    def __call__(self, msg, priority = 1):
        self._print(msg, priority)

    def _print(self, msg, priority = 1):
        if self._priority >= priority:
            sys.stdout.write("%s\n" % msg)


class Debug(Channel):
    def _print(self, msg, priority = 1):
        if self._priority >= priority:
            stack = inspect.stack()
            indent = "".join([ " " for i in range(len(stack) - 2) ])

            self._printFrame(stack[2], msg, indent)

    def _printFrame(self, frame, msg = None, indent = ""):
        (fr, f, l, fn, c, i) = frame
        f = re.sub(r'^.*libgsync/', "", f)
        f = re.sub(r'/__init__.py', "/", f)
        if msg is not None:
            super(Debug, self)._print(
                "DEBUG: %s%s:%d:%s(): %s" % (indent, f, l, fn, msg)
            )
        else:
            super(Debug, self)._print(
                "DEBUG: %s%s:%d:%s()" % (indent, f, l, fn)
            )

    def stack(self):
        super(Debug, self)._print("DEBUG: BEGIN STACK TRACE")

        stack = inspect.stack()[1:]
        for frame in stack:
            self._printFrame(frame, indent="    ")

        super(Debug, self)._print("DEBUG: END STACK TRACE")

    def exception(self, e = "Exception"):
        if isinstance(e, Exception):
            super(Debug, self)._print("DEBUG: %s: %s" % (
                repr(e), str(e)
            ), -1)

        import traceback
        super(Debug, self)._print("DEBUG: %s: %s" % (
            repr(e), "".join(traceback.format_tb(sys.exc_info()[2]))
        ), -1)


class Verbose(Channel):
    pass


class Itemize(object):
    def __call__(self, changes, filename):
        sys.stdout.write("%11s %s\n" % (str(changes), filename))


class Progress(object):
    def __init__(self, enableOutput = True, callback = None):
        self._callback = callback
        self._enableOutput = enableOutput
        self._start = datetime.now()

        self.bytesWritten = 0L
        self.bytesTotal = 0L
        self.percentage = 0
        self.timeTaken = 0

        self._print()

    def _print(self):
        if self._enableOutput:
            ss = int(self.timeTaken)
            s = ss % 60
            m = int(ss / 60) % 60
            h = int((ss / 60) / 60) % 60

            sys.stdout.write("\r%12d %3d%% %11s %10s" % (
                self.bytesWritten, self.percentage, self.rate(),
                    "%d:%02d:%02d" % (h, m, s)
            ))
        
    def __call__(self, status):
        self.timeTaken = (datetime.now() - self._start).seconds
        self.bytesWritten = long(status.resumable_progress)
        self.percentage = int(status.progress() * 100.0)
        self.bytesTotal = status.total_size

        self._print()

        if self._callback is not None:
            self._callback(status)

    def rate(self):
        rate = float(self.bytesWritten) / max(0.1, float(self.timeTaken))

        for x in [ 'B', 'KB', 'MB', 'GB', 'TB' ]:
            if rate < 1024.0:
                return "%3.2f%s/s" % (rate, x)
            rate /= 1024.0

    def complete(self, bytesWritten):
        self.timeTaken = (datetime.now() - self._start).seconds
        self.bytesWritten = bytesWritten

        if self.bytesTotal > 0L:
            self.percentage = int(
                (float(self.bytesWritten) / float(self.bytesTotal)) * 100.0
            )
        elif self.bytesWritten == 0L:
            self.percentage = 100
        else:
            self.percentage = 0

        if self._enableOutput:
            self._print()
            sys.stdout.write("\n")

verbose = Verbose()
debug = Debug()
itemize = Itemize()

if os.environ.get('GSYNC_DEBUG', '0') == '1':
    debug.enable()
