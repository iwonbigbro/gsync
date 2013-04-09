# Copyright (C) 2013 Craig Phillips.  All rights reserved.

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
        print(msg)


class Debug(Channel):
    def _print(self, msg):
        print("DEBUG: %s" % msg)

class Verbose(Channel):
    pass

verbose = Verbose()
debug = Debug()
