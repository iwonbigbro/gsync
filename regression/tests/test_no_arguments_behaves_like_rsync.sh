#!/bin/bash

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

function test_copying_to_missing_target_directory() {
    local args=( $SRC $TESTTMP/rsync_nodir )

    rsync -i "${args[@]}" >$TESTTMP/rsync.out
    rsync_e=$?

    gsync -i "${args[@]}" >$TESTTMP/gsync.out
    gsync_e=$?

    assertEqual $rsync_e $gsync_e
    assertNoDiff $TESTTMP/rsync.out $TESTTMP/gsync.out
}
