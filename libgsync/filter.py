# Copyright (C) 2013 Craig Phillips.  All rights reserved.

import re

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
MODIFIERS = "(%s)" % "|".join([ m for r, m in RULEMOD_PAIRS ])
EXPR_RULE_MOD_PATTERN = "\s*(%s),\s*(%s)\s*(\S+)" % (RULES, MODIFIERS)
EXPR_RULE_PATTERN = "\s*(%s)\s*(\S+)" % (RULES)
EXPR_MOD_PATTERN = "\s*,?\s*(%s)\s*(\S+)" % (MODIFIERS)
EXPR = r"^(?:%s|%s|%s)$" % (
    EXPR_RULE_MOD_PATTERN,
    EXPR_MOD_PATTERN,
    EXPR_RULE_PATTERN,
)

def glob(pattern, path):
    # TODO:
    return False

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
        rule, mod, pattern = None, None, None
        match = re.match(EXPR, rule_string)

        if match is None:
            return

        if len(match.groups()) > 2:
            rule, mod, pattern = match.groups()
        elif len(match.groups()) > 1:
            mod, pattern = match.groups()
            mod = mod[0].upper()

            if mod == "I": mod = "+"
            elif mod == "E": mod = "-"
            elif mod == "D": mod = ":"
            elif mod == "M": mod = "."
        else:
            # Invalid rule.
            return

        if mod == ":":
            self.dir_merge = pattern
            return
        elif mod in ".":
            # Stop and load some more rules.
            self.loadRules(pattern)
            return

        self.rules.append((mod, pattern))


Filter = FilterObject()
