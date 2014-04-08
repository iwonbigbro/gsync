#!/bin/bash

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

function test_symlinks_are_not_implicitly_followed_remotely() {
    local src=$LOCAL_TESTTMP/
    local dst=$REMOTE_TESTTMP/

    mkdir -p $src/a_directory

    echo "test file" >$src/a_file.txt
    ln -s a_file.txt $src/a_symlink.txt
    ln -s a_directory $src/a_symlink_dir

    assert gsync -irc $src/ $dst/

    rm -rf $src/
    mkdir -p $src/

    assert gsync -irc $dst/ $src/

    assertIsFile $src/a_file.txt
    assertIsLink $src/a_symlink.txt

    assertIsDir $src/a_directory
    assertIsLink $src/a_symlink_dir
}

function test_symlinks_are_not_implicitly_followed_locally() {
    local src=$LOCAL_TESTTMP/dir_a/
    local dst=$LOCAL_TESTTMP/dir_b/

    rm -rf $dst/
    mkdir -p $dst/

    mkdir -p $src/a_directory

    echo "test file" >$src/a_file.txt
    ln -s a_file.txt $src/a_symlink.txt
    ln -s a_directory $src/a_symlink_dir

    assert gsync -irc $src/ $dst/

    rm -rf $src/
    mkdir -p $src/

    assert gsync -irc $dst/ $src/

    assertIsFile $src/a_file.txt
    assertIsLink $src/a_symlink.txt

    assertIsDir $src/a_directory
    assertIsLink $src/a_symlink_dir
}
