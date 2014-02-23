#!/usr/bin/env python

import sys, os

paths = sys.argv[1:]

fsenc = sys.getfilesystemencoding()

for p in paths:
    print "p = %s" % repr(p)

    if not isinstance(p, unicode):
        up = unicode(p, encoding = "latin-1", errors = "strict")
        
    print "up = %s" % repr(up)
    print "up.utf8 = %s" % up.encode("utf8")

    print "Command line file exists = %s" % os.path.exists(p)
    print "Unicode file exists = %s" % os.path.exists(up)
    print "%s file exists = %s" % (fsenc, os.path.exists(up.encode(fsenc)))
