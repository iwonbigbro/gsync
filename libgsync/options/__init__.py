#!/usr/bin/env python

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

# This requires some explaining.  The point of this metaclass excercise is to
# create a static abstract class that is in one way or another, dormant until
# queried.  I experimented with creating a singlton on import, but that did
# not quite behave how I wanted it to.  See now here, we are creating a class
# called GsyncOptions, that on import, will do nothing except state that its
# class creator is GsyncOptionsType.  This means, docopt doesn't parse any
# of the help document, nor does it start processing command line options.
# So importing this module becomes really efficient.  The complicated bit
# comes from requiring the GsyncOptions class to be static.  By that, I mean
# any property on it, may or may not exist, since they are not statically
# defined; so I can't simply just define the class with a whole bunch of
# properties that are @property @staticmethods.
#
# So here's how it works:
#
# Executing 'from libgsync.options import GsyncOptions' does nothing more
# than load up this module, define the Type and the Class and import them
# into the callers namespace.  Simple.
#
# Invoking 'GsyncOptions.debug' for the first time, or any other property
# causes the __metaclass__ __getattr__ method to be called, since the class
# is not instantiated as a class instance yet.  The __getattr__ method on
# the type then initialises the class (GsyncOptions) via the __initialiseClass
# method.  This is the first and only time the class will actually have its
# dictionary statically populated.  The docopt module is invoked to parse the
# usage document and generate command line options from it.  These are then
# paired with their defaults and what's in sys.argv.  After all that, we
# setup some dynamic properties that could not be defined by their name in
# the usage, before everything is then transplanted onto the actual class
# object (or static class GsyncOptions).
#
# Another piece of magic, is to allow command line options to be set in
# in their native form and be translated into argparse style properties.
#
# Finally, the GsyncListOptions class is actually where the options are
# stored.  This only acts as a mechanism for storing options as lists, to
# allow aggregation of duplicate options or options that can be specified
# multiple times.  The __getattr__ call hides this by default, returning the
# last item in a property's list.  However, if the entire list is required,
# calling the 'list()' method on the GsyncOptions class, returns a reference
# to the GsyncListOptions class, which contains all of the same properties
# but as lists and without the duplication of having them as both lists and
# static singlton values.
#
# So this actually means that GsyncOptions is actually a static proxy class...
#
# ...And all this is neatly hidden within a closure for safe keeping.
def GetGsyncOptionsType():
    # The actual class where the options data are stored.
    class Options(object):
        __initialised = False

    # An type interface to the static GsyncListOptions class.
    class GsyncListOptionsType(type):
        def __initialiseClass(cls):
            from docopt import docopt
            from libgsync.options import doc
            from libgsync import __version__

            options = docopt(
                doc.__doc__ % __version__,
                version = __version__,
                options_first = True
            )

            paths = options.pop('<path>', None)
            setattr(cls, "destination_path", paths.pop() if paths else None)
            setattr(cls, "source_paths", paths)
            setattr(cls, "options", options)

            for k, v in options.iteritems():
                setattr(cls, k, v)

        def __getattr__(cls, name):
            if not Options._Options__initialised:
                cls.__initialiseClass()
                Options._Options__initialised = True

            if not hasattr(Options, name):
                type.__setattr__(Options, name, [ None ])

            return getattr(Options, name)

        def __setattr__(cls, name, value):
            # Substitut option names: --an-option-name for an_option_name
            import re
            name = re.sub(r'^__', "", re.sub(r'-', "_", name))
            listvalue = []

            # Ensure value is converted to a list type for Options
            if isinstance(value, list):
                if value:
                    listvalue = [] + value
                else:
                    listvalue = [ None ]
            else:
                listvalue = [ value ]

            type.__setattr__(Options, name, listvalue)


    # Static interface to options as lists.
    class GsyncListOptions(object):
        __metaclass__ = GsyncListOptionsType


    # An type interface to the static GsyncOptions class.
    class GsyncOptionsType(GsyncListOptionsType):
        def list(cls):
            return GsyncListOptions

        def __getattr__(cls, name):
            return GsyncListOptionsType.__getattr__(cls, name)[-1]


    # Cleanup this module to prevent tinkering.
    import sys
    module = sys.modules[__name__]
    del module.__dict__['GetGsyncOptionsType']

    return GsyncOptionsType

# Our singlton abstract proxy class for accessing options.
class GsyncOptions(object):
    __metaclass__ = GetGsyncOptionsType()
