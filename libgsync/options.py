# Copyright (C) 2013 Craig Phillips.  All rights reserved.

class EUnsupportedOption(Exception):
    def __init__(self, option):
        self.option = option

    def __str__(self):
        return "Unsupported option: %s" % self.option


class Options():
    _opt_itemizeChanges = False
    _opt_ignoreExisting = False
    _opt_relative = False
    _opt_recursive = False
    _opt_dirs = False
    _opt_debug = False
    _opt_verbose = 0

    def initialiseOptions(self, options):
        if options is not None:
            for k, v in options.iteritems():
                if k == '--itemize-changes':
                    self._opt_itemizeChanges = v
                elif k == '--ignore-existing':
                    self._opt_ignoreExisting = v
                elif k == '--recursive':
                    self._opt_recursive = v
                elif k == '--relative':
                    self._opt_relative = v
                elif k == '--dirs':
                    self._opt_dirs = v
                elif k == '--debug':
                    self._opt_debug = v
                elif k == '--verbose':
                    self._opt_verbose += 1
                else:
                    if v is not None and v != False:
                        raise EUnsupportedOption(k)
