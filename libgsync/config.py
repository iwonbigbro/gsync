#!/usr/bin/env python

from libgsync.output import debug

class Data(object):
    def __init__(self, path, encoder="pickle"):
        self._path = path
        self.set(None)

        if encoder == "pickle":
            import pickle as _encoder
        elif encoder == "json":
            try:
                import simplejson as _encoder
            except:
                import json as _encoder

        self._encoder = _encoder
    
    def load(self):
        f, data = None, None
        try:
            f = open(self._path, "r")
            data = f.read()
        except OSError: pass
        except IOError: pass
        finally:
            if f is not None:
                f.close()

        self.set(data)
        return self._data

    def save(self, data = None):
        if data is not None:
            self.set(data)

        sdata = str(self)
        f = None
        try:
            f = open(self._path, "w")
            f.write(sdata)
        except OSError: pass
        except IOError: pass
        finally:
            if f is not None:
                f.close()

    def get(self):
        return self._data

    def __str__(self):
        return self._sdata

    def set(self, data):
        if data is None:
            self._data = None
            self._sdata = ""
            return

        if isinstance(data, str):
            sdata = data
            data = self._encoder.loads(sdata)
        else:
            sdata = self._encoder.dumps(data)

        self._sdata = sdata
        self._data = data
