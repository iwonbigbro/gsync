# Copyright (C) 2013 Craig Phillips.  All rights reserved.

class DriveFile(object):
    def __init__(self, **kwargs):
        self._dict = dict(kwargs.items())

    def keys(self): return self._dict.keys()
    def values(self): return self._dict.values()
    def items(self): return self._dict.items()
    def iteritems(self): return self._dict.iteritems()
    def dict(self): return dict(self.items())

    def __getattr__(self, key):
        return self._dict.get(key, self.__dict__.get(key))

    def __getitem__(self, key):
        return self._dict[key]

    def __repr__(self):
        return "DriveFile(**{ %s })" % ", ".join([
            "%s: %s" % (repr(k), repr(v)) for k, v in self._dict.iteritems()
        ])
