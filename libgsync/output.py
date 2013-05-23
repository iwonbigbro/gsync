# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import sys, inspect, re

class Channel():
    _priority = -1 

    def enable(self):
        if self._priority < 0:
            self._priority = 0
        self._priority += 1

    def __call__(self, msg, priority = 1):
        if self._priority >= priority:
            self._print(msg)

    def _print(self, msg):
        sys.stdout.write("%s\n" % msg)


class Debug(Channel):
    def _print(self, msg):
        self._printFrame(inspect.stack()[2], msg)

    def _printFrame(self, frame, msg = None, indent = ""):
        (fr, f, l, fn, c, i) = frame
        f = re.sub(r'^.*dist-packages/', "", f)
        if msg is not None:
            sys.stderr.write("DEBUG: %s%s:%d:%s(): %s\n" % 
                (indent, f, l, fn, msg))
        else:
            sys.stderr.write("DEBUG: %s%s:%d:%s()\n" % 
                (indent, f, l, fn))

    def stack(self):
        sys.stderr.write("DEBUG: BEGIN STACK TRACE\n")

        stack = inspect.stack()[1:]
        for frame in stack:
            self._printFrame(frame, indent="    ")

        sys.stderr.write("DEBUG: END STACK TRACE\n")

    def exception(self, e = None):
        if e is None: e = "Exception"

        import traceback
        sys.stderr.write("DEBUG: %s: %s" % (
            repr(e),
            "".join(traceback.format_tb(sys.exc_info()[2]))
        ))

class Verbose(Channel):
    pass


class Itemize(object):
    def __call__(self, changes, filename):
        sys.stdout.write("%11s %s\n" % (str(changes), filename))

verbose = Verbose()
debug = Debug()
itemize = Itemize()
