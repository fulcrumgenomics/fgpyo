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

banner "Executing in conda environment ${CONDA_DEFAULT_ENV} in directory fgpyo"
run "Style Checking" "ruff format fgpyo"
run "Linting"        "ruff check --fix fgpyo"
run "Type Checking"  "mypy -p fgpyo --config $parent/mypy.ini"
run "Unit Tests"     "python -m pytest -vv -r sx tests"
run "Make docs"      "poetry run mkdocs build --strict"

if [ -z "$failures" ]; then
    banner "Checks Passed"
else
    banner "Checks Failed with failures in: $failures"
    exit 1
fi
