#!/bin/bash

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

function test_copying_to_missing_target_directory() {
    local src=$(firstword /usr/lib/python*)
    local dst=$LOCAL_TESTTMP/rsync_nodir

    assert rsync -i $src $dst >$LOCAL_TESTTMP/rsync.out

    rm -rf $dst
    mkdir $dst

    assert gsync -i $src $dst >$LOCAL_TESTTMP/gsync.out

    assertNoDiff $LOCAL_TESTTMP/rsync.out $LOCAL_TESTTMP/gsync.out
}
