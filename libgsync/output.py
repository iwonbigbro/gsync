# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import sys, inspect, re

class Channel(object):
    _priority = -1 

    def enable(self):
        if self._priority < 0:
            self._priority = 0
        self._priority += 1

    def enabled(self):
        return self._priority > 0

    def __call__(self, msg, priority = 1):
        self._print(msg, priority)

    def _print(self, msg, priority = 1):
        if self._priority >= priority:
            sys.stdout.write("%s\n" % msg)


class Debug(Channel):
    def _print(self, msg, priority = 1):
        stack = inspect.stack()
        indent = "".join([ " " for i in range(len(stack) - 2) ])

        self._printFrame(stack[2], msg, indent)

    def _printFrame(self, frame, msg = None, indent = ""):
        (fr, f, l, fn, c, i) = frame
        f = re.sub(r'^.*dist-packages/', "", f)
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

    def exception(self, e = None):
        if e is None: e = "Exception"

        import traceback
        super(Debug, self)._print("DEBUG: %s: %s" % (
            repr(e), "".join(traceback.format_tb(sys.exc_info()[2]))
        ))


class Verbose(Channel):
    pass


class Itemize(object):
    def __call__(self, changes, filename):
        sys.stdout.write("%11s %s\n" % (str(changes), filename))


verbose = Verbose()
debug = Debug()
itemize = Itemize()
