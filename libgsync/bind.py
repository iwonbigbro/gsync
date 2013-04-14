# Copyright (C) 2013 Craig Phillips.  All rights reserved.

class EBindNoContext(Exception):
    pass

class EBindNoFunc(Exception):
    pass

class bind(object):
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
            raise EBindNoFunc

        if context:
            return func(context, *xargs)

        return func(*xargs)
