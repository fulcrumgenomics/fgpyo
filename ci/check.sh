#!/usr/bin/env bash

# Require uv
if [ ! -x "$(command -v uv)" ]; then
    echo >&2 "Error: 'uv' not found."
    echo >&2 "Install via https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

uv run poe fix-and-check-all
uv run poe build-docs
