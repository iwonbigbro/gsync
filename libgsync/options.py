# Copyright (C) 2013 Craig Phillips.  All rights reserved.

class GsyncOptions():
    # Internal option for determining destination file type.
    force_dest_file = None

    pass

def initialise(options):
    import re
    for k, v in options.iteritems():
        optname = re.sub(r'^__', "", re.sub(r'-', "_", k))
        setattr(GsyncOptions, optname, v)
