#!/usr/bin/env bash

function banner() {
    echo
    echo "================================================================================"
    echo -e "$*"
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
        echo Passed "$name": "[$cmd]"
    else
        echo Failed "$name": "[$cmd]"
        if [ -z "$failures" ]; then
            failures="$failures $name"
        else
            failures="$failures, $name"
        fi
    fi
}

run "Checking lockfile"    "uv lock --check"
run "Updating environment" "uv sync --locked"
run "Style Checking"       "uv run ruff format fgpyo tests"
run "Linting"              "uv run ruff check --fix fgpyo tests"
run "Type Checking"        "uv run mypy fgpyo tests --config pyproject.toml"
run "Unit Tests"           "uv run pytest -vv -r sx tests"
run "Make docs"            "uv run mkdocs build --strict"

if [ -z "$failures" ]; then
    banner "Checks Passed"
else
    banner "Checks Failed with failures in: $failures"
    exit 1
fi
