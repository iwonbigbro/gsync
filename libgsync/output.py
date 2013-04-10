# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import sys

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
        sys.stderr.write("DEBUG: %s\n" % msg)


class Verbose(Channel):
    pass


class Itemize(object):
    def __call__(self, changes, filename):
        sys.stdout.write("%11s %s\n" % (str(changes), filename))

verbose = Verbose()
debug = Debug()
itemize = Itemize()
