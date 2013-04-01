# Copyright (C) 2013 Craig Phillips.  All rights reserved.

class Channel():
    _enabled = False

    def enable(self):
        self._enabled = True


    def __call__(self, msg):
        if self._enabled:
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
