#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright (C) 2013-2014 Craig Phillips.  All rights reserved.

"""Defines the client object to be used during authentication"""

# pylint: disable-msg=C0103

client_obj = {
    "installed": {
        "client_id": "542942405111.apps.googleusercontent.com",
        "client_secret": "Y4iSAluo7pCY57m8HFOfv2W_",
        "redirect_uris": [
            "http://localhost", "urn:ietf:oauth:2.0:oob"
        ],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://accounts.google.com/o/oauth2/token"
    }
}
