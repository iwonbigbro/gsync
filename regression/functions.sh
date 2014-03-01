#!/bin/bash

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

tests=0
passed=0
failed=0
skipped=0
errors=0

function fail() {
    e=$1 ; shift
    echo "FAIL"
    echo " ... "
    __backtrace
    printf >&4 "F"
    exit $e
}

function error() {
    e=$1 ; shift
    echo "ERROR"
    echo " ... "
    __backtrace
    printf >&4 "E"
    exit $e
}

function skip() {
    e=$1 ; shift
    echo "SKIP"
    echo " ... "
    printf >&4 "s"
    exit $e
}

function pass() {
    echo "ok"
    printf >&4 "."
    exit 0
}

function exitwith() {
    (( $1 == 0 )) && pass
    (( $1 < 127 )) && fail $1
    (( $1 == 127 )) && error $1
    (( $1 > 127  )) && skip $1
}

function update_stats() {
    (( tests++ ))

    (( $1 == 0 )) && (( pass++ ))
    (( $1 >0 && $1 < 127 )) && (( failed++ ))
    (( $1 == 127 )) && (( errors++ ))
    (( $1 > 127  )) && (( skipped++ ))

    cat >$OUTPUT/stats <<STATS
tests=$tests
passed=$passed
skiped=$skipped
failed=$failed
errors=$errors
STATS
}

function sync_stats() {
    . $OUTPUT/stats
}

function summary() {
    cat <<SUMMARY
--------------------------------------------------------------------------------
Ran $tests tests in $SECONDS seconds
--------------------------------------------------------------------------------
   Passed: $passed
  Skipped: $skipped
   Failed: $failed
   Errors: $errors
--------------------------------------------------------------------------------
$(if (( $failed > 0 || $errors > 0 )) ; then
    echo "FAILURE"
else
    echo "SUCCESS"
fi)
--------------------------------------------------------------------------------
SUMMARY
}

function max() { printf "%d\n" "$@" | sort -n | tail -1 ; }
function min() { printf "%d\n" "$@" | sort -nr | tail -1 ; }

function __backtrace() {
    local i=${1:-1}
    set +x

    while true ; do
        read lineno func src < <(caller $i)
        [[ $? == 0 ]] || break
        (( i++ ))

        printf '  File "%s", line %d, in %s\n' $src $lineno $func

        awk 'NR == '$lineno' {
            printf "    %s\n", gensub(/^\ */, "", "", $0)
            exit
        }' $src
    done
}

function assertionError() {
    ( fail 1 )
    echo >&2 "AssertionError: $*"
    exit 1
}

function assertEqual() {
    [[ $1 == $2 ]] || assertionError "Expected '$1' got '$2'"
}

function assertNoDiff() {
    diff -U3 >$TESTTMP/diff.tmp $1 $2 || assertionError \
        "Files differ $(echo ; cat $TESTTMP/diff.tmp)"
}
