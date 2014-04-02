#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013 Craig Phillips.  All rights reserved.

"""
Defines the filter feature of gsync, as specified by --filter like options.
"""

import re, fnmatch
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
RULES = r"(%s)" % "|".join([ r for r, m in RULEMOD_PAIRS ])
MODIFIERS = r"([%s])" % "".join([ m for r, m in RULEMOD_PAIRS ])
EXPR_RULE_MOD_PATTERN = r"\s*%s,\s*%s\s*(\S+)" % (RULES, MODIFIERS)
EXPR_RULE_PATTERN = r"\s*%s\s*(\S+)" % (RULES)
EXPR_MOD_PATTERN = r"\s*,?\s*%s\s*(\S+)" % (MODIFIERS)
EXPR_LIST = (
    EXPR_RULE_MOD_PATTERN,
    EXPR_MOD_PATTERN,
    EXPR_RULE_PATTERN,
)


class FilterException(Exception):
    """For exceptions that occur relating to filters or filtering."""
    pass


class FilterObject(object):
    """Defines a singleton loadable filter definition."""

    def __init__(self):
        self.rules = []
        self.pathcache = {}
        self.merge_dir = ""
    
    def get_modifier(self, path):
        """Returns a rule modifier that matches the given path"""

        modifer = self.pathcache.get(path)
        if modifer is None:
            return modifer

        for modifer, pattern in self.rules:
            if fnmatch.fnmatch(path, pattern):
                return self.pathcache.setdefault(path, modifer)

        return None

    def load_rules(self, path, modifier=""):
        """Loads filter rules from the file specified by 'path'."""

        with open(path, "r") as fd:
            for line in fd:
                self.add_rule(modifier + " " + line)
                
    def add_rules(self, rules, modifier = ""):
        """
        Adds rules to the filter object, specified with 'rules' and an
        optional modifier, where rules do not contain modifiers.
        """
        for rule in rules:
            self.add_rule(modifier + " " + rule)

    def add_rule(self, rule_string):
        """
        Adds a single rule to the filter object.
        """
        match = None
        for expr in EXPR_LIST:
            match = re.match(expr, rule_string)
            if match is not None:
                break

        if match is None:
            return

        ngroups = len(match.groups())
        debug("%s matched %d groups" % (repr(rule_string), ngroups))
        debug(" * [%s]" % ",".join([
            x if x else "" for x in match.groups()
        ]))

        if ngroups == 3:
            mod, pattern = match.groups(2, 3)

        elif ngroups == 2:
            mod, pattern = match.groups(1, 2)
            mod = mod[0].upper()

            if mod == "I":
                mod = "+"
            elif mod == "E":
                mod = "-"
            elif mod == "D":
                mod = ":"
            elif mod == "M":
                mod = "."
        else:
            raise FilterException("Invalid rule: %s" % rule_string)

        if mod == ":":
            self.merge_dir = pattern
            return

        if mod == ".":
            # Stop and load some more rules.
            self.load_rules(pattern)
            return

        self.rules.append((mod, pattern))


Filter = FilterObject() # pylint: disable-msg=C0103
