#!/bin/bash

function banner() {
    echo
    echo "================================================================================"
    echo $*
    echo "================================================================================"
    echo
}

#####################################################################
# Takes two parameters, a "name" and a "command".
# Runs the command and prints out whether it succeeded or failed, and
# also tracks a list of failed steps in $failures.
#####################################################################
function run() {
    local name=$1
    local cmd=$2

    banner "Running $name [$cmd]"
    set +e
    $cmd
    exit_code=$?
    set -e

    if [[ $exit_code == 0 ]]; then
        echo Passed $name: "[$cmd]"
    else
        echo Failed $name: "[$cmd]"
        if [ -z "$failures" ]; then
            failures="$failures $name"
        else
            failures="$failures, $name"
        fi
    fi
}

parent=$(cd $(dirname $0) && pwd -P)

# If the script is invoked with --check only have black check, otherwise have it fix!
black_extra_args=""
if [[ "$1" == "--check" ]]; then
    black_extra_args="--check"
fi

banner "Executing in conda environment ${CONDA_DEFAULT_ENV} in directory ${root}"
run "Unit Tests"     "python -m pytest -vv -r sx fgpyo"
run "Import Sorting" "isort --force-single-line-imports --profile black fgpyo"
run "Style Checking" "black --line-length 99 $black_extra_args fgpyo"
run "Linting"        "flake8 --config=$parent/flake8.cfg fgpyo"
run "Type Checking"  "mypy -p fgpyo --config $parent/mypy.ini"

if [ -z "$failures" ]; then
    banner "Checks Passed"
else
    banner "Checks Failed with failures in: $failures"
    exit 1
fi
