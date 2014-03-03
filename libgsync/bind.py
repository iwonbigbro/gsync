# Copyright (C) 2013 Craig Phillips.  All rights reserved.

"""Module for providing a function paramater binding closure"""

class BindNoFuncError(Exception):
    pass

class bind(object):
    """Binds a function to a set of arguments and a defined context"""

    def __init__(self, func, context, *args):
        self.__f = func
        self.__c = context
        self.__a = args

    def __call__(self, *args):
        func, context = self.__f, self.__c
        xargs = () + self.__a + args

        if isinstance(func, str):
            func = context.__class__.__dict__.get(func, None)

        if not callable(func):
            raise BindNoFuncError

        if context:
            return func(context, *xargs)

        return func(*xargs)
