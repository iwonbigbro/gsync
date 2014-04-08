#!/bin/bash

# Copyright (C) 2014 Craig Phillips.  All rights reserved.

rprog=$(readlink -f $0)
prog=${rprog##*/}
progdir=${rprog%/*}

export OUTPUT=$progdir/output

function usage() {
    cat <<USAGE
Usage: $prog [options]
Options:
    --coverage         Run with python code coverage analysis.
    --verbose          Verbose output.
    --verbose-tty      Verbose output when a tty is present.
    --verbose-no-tty   Verbose output when a tty is not present.
    --no-cleanup       Don't cleanup temporary files.

Copyright (C) 2014 Craig Phillips.  All rights reserved.
USAGE
}

while (( $# > 0 )) ; do
    case $1 in
    (--verbose)
        verbose=1
        ;;
    (--verbose-tty)
        [[ -t 0 ]] && verbose=1
        ;;
    (--verbose-no-tty)
        [[ -t 0 ]] || verbose=1
        ;;
    (--coverage)
        COVERAGE_PROCESS_START=1
        ;;
    (--no-cleanup)
        nocleanup=1
        ;;
    (--clean)
        rm -r${verbose:+v}f $OUTPUT
        exit $?
        ;;
    (--help)
        usage
        exit 0
        ;;
    (*)
        echo >&2 "$prog: Invalid argument: $1"
        exit 1
        ;;
    esac
    shift
done

if [[ $COVERAGE_PROCESS_START ]] ; then
    export COVERAGE_DIR=$OUTPUT/coverage
    export COVERAGE_PROCESS_START=$COVERAGE_DIR/regression.ini

    rm -rf $COVERAGE_DIR
    mkdir -p $COVERAGE_DIR

    cat >$COVERAGE_PROCESS_START <<CONFIG
[run]
branch = True
parallel = True
data_file = $COVERAGE_DIR/regression.dat
CONFIG
fi

mkdir -p $OUTPUT

declare -A errmap=( [0]="." [1]="F" [2]="s" )

if [[ $verbose ]] ; then
    exec 4>$OUTPUT/summary.txt
else
    exec 4> >(tee $OUTPUT/summary.txt)
fi

trap "echo >&4 ; echo >&2 KeyboardInterrupt" INT

. $progdir/functions.sh || exit 127

SECONDS=0
for testpath in $(find $progdir/tests -type f -name 'test_*.sh') ; do
    testname=${testpath##*/}
    testname=${testname%/.sh}

    (
        exec 3>$OUTPUT/$testname-debug.log
        BASH_XTRACEFD=3 ; set -x

        if [[ $verbose ]] ; then
            exec 1> >(tee $OUTPUT/$testname.log) 2>&1
        else
            exec 1>$OUTPUT/$testname.log 2>&1
        fi

        mkdir -p $OUTPUT/tmp
        
        export TESTCASETMP=$(mktemp -d $OUTPUT/tmp/$testname.XXXXXXXX)
        [[ $nocleanup ]] || trap "rm -rf $TESTCASETMP" EXIT

        printf "Importing: $testname ... "

        . $testpath || error $?

        echo "ok"

        for fn in $(declare -f | awk '/^test_/ { print $1 }') ; do
            export LOCAL_TESTTMP=$TESTCASETMP/$fn
            export REMOTE_TESTTMP=drive:///gsync_regression/tmp/$fn
            mkdir -p $LOCAL_TESTTMP

            printf "Running: $fn ... "
            ( $fn ; exitwith $? )
            ret=$?
            update_stats $ret

            [[ $ret == 0 || $e == 1 ]] || e=$ret
        done

        exit ${e:-0}
    ) || e=${e:-$?}

    sync_stats
done
echo

summary

if [[ $COVERAGE_PROCESS_START ]] ; then
    python -m coverage combine \
        --rcfile $COVERAGE_PROCESS_START

    python -m coverage html \
        --rcfile $COVERAGE_PROCESS_START \
        --include "*/libgsync/*" \
        --directory $COVERAGE_DIR
fi

exit ${e:-0}
