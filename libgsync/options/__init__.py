# Copyright (C) 2013 Craig Phillips.  All rights reserved.

class _GsyncListOptions(object):
    _initialised = False

class _GsyncOptions(type):
    def __init(self):
        if _GsyncListOptions._initialised: return

        from docopt import docopt
        from libgsync.options import doc
        from libgsync import get_version

        version = get_version()
        options = docopt(
            doc.__doc__ % version,
            version = version,
            options_first = True
        )

        paths = options.pop('<path>', None)
        setattr(self, "destination_path", paths.pop())
        setattr(self, "source_paths", paths)
        setattr(self, "options", options)

        for k, v in options.iteritems():
            setattr(self, k, v)

        _GsyncListOptions._initialised = True

    def list(self):
        return _GsyncListOptions

    def __getattr__(self, name):
        self.__init()
        return getattr(_GsyncListOptions, name)[-1]

    def __setattr__(self, name, value):
        # Substitut option names: --an-option-name for an_option_name
        import re
        name = re.sub(r'^__', "", re.sub(r'-', "_", name))
        listvalue = []

        # Ensure value is converted to a list type for GsyncListOptions
        if isinstance(value, list):
            if value:
                listvalue = [] + value
            else:
                listvalue = [ None ]
        else:
            listvalue = [ value ]

        type.__setattr__(_GsyncListOptions, name, listvalue)

class GsyncOptions(object):
    __metaclass__ = _GsyncOptions
