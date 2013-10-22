# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import re
from libgsync.output import debug

RULEMOD_PAIRS = [
    ("exclude", "-"),
    ("include", "+"),
    ("hide", "H"),
    ("show", "S"),
    ("protect", "P"),
    ("risk", "R"),
    ("dir-merge", ":"),
    ("merge", "."),
]
RULES = "(%s)" % "|".join([ r for r, m in RULEMOD_PAIRS ])
MODIFIERS = "([%s])" % "".join([ m for r, m in RULEMOD_PAIRS ])
EXPR_RULE_MOD_PATTERN = "\s*%s,\s*%s\s*(\S+)" % (RULES, MODIFIERS)
EXPR_RULE_PATTERN = "\s*%s\s*(\S+)" % (RULES)
EXPR_MOD_PATTERN = "\s*,?\s*%s\s*(\S+)" % (MODIFIERS)
EXPR_LIST = (
    EXPR_RULE_MOD_PATTERN,
    EXPR_MOD_PATTERN,
    EXPR_RULE_PATTERN,
)

def glob(pattern, path):
    # TODO:
    return False

class FilterException(Exception):
    pass

class FilterObject(object):
    def __init__(self):
        self.rules = []
        self.pathcache = {}
        self.merge_dir = ""
    
    def getModifier(self, path):
        modifer = self.pathcache.get(path)
        if modifer is None:
            return modifer

        for modifer, pattern in rules:
            if self.match(pattern, path):
                return self.pathcache.setdefault(path, modifer)

        return None

    def loadRules(self, path, modifier = ""):
        with open(path, "r") as f:
            for line in f:
                self.addRule(modifier + " " + line)
                
    def addRules(self, rules, modifier = ""):
        for rule in rules:
            self.addRule(modifier + " " + rule)

    def addRule(self, rule_string):
        match, rule, mod, pattern = None, None, None, None

        for expr in EXPR_LIST:
            match = re.match(expr, rule_string)
            if match is not None:
                break

        if match is None:
            return

        ngroups = len(match.groups())
        debug("%s matched %d groups" % (repr(rule_string), ngroups))
        debug(" * [%s]" % ",".join([ x if x else "" for x in match.groups() ]))

        if ngroups == 3:
            rule, mod, pattern = match.groups()
        elif ngroups == 2:
            mod, pattern = match.groups()
            mod = mod[0].upper()

            if mod == "I": mod = "+"
            elif mod == "E": mod = "-"
            elif mod == "D": mod = ":"
            elif mod == "M": mod = "."
        else:
            raise FilterException("Invalid rule: %s" % rule_string)

        if mod == ":":
            self.dir_merge = pattern
            return
        elif mod in ".":
            # Stop and load some more rules.
            self.loadRules(pattern)
            return

        self.rules.append((mod, pattern))


Filter = FilterObject()
