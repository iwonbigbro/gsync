# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import re

class EUnsupportedOption(Exception):
    def __init__(self, option):
        self.option = option

    def __str__(self):
        return "Unsupported option: %s" % self.option


class EOptionReadOnly(Exception):
    pass


class Options():
    def initialiseOptions(self, options):
        if options is None:
            return

        for k, v in options.iteritems():
            optname = re.sub(r'^__', "_opt_", re.sub(r'-', "_", k))
            self.__dict__[optname] = v
