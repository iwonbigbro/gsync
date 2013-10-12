# Copyright (C) 2013 Craig Phillips.  All rights reserved.

class GsyncOption(object):
    def __init__(self, name, value):
        self.name = name
        if isinstance(value, list):
            self.value = [] + value
        else:
            self.value = [ value ]

    def __repr__(self):
        return "GsyncOption('%s', %s)" % (self.name, repr(self.value))

    def __str__(self): return self.value[-1]
    def __getitem__(self, index): return self.value[index]

class GsyncOptions(object):
    # Internal option for determining destination file type.
    force_dest_file = None


def initialise(options):
    import re
    for k, v in options.iteritems():
        optname = re.sub(r'^__', "", re.sub(r'-', "_", k))
        setattr(GsyncOptions, optname, GsyncOption(optname, v))
