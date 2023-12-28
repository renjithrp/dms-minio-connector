#!/bin/bash

set_pythonpath() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
    export PYTHONPATH="$script_dir/src"
}

load_environment() {
    source "$(dirname "$0")/env" 2> /dev/null || source "$(dirname "$0")/env" # For macOS environments
}

start_server() {
    local bind_address="${BIND_ADDRESS:=127.0.0.1:9081}"
    gunicorn --bind "$bind_address" wsgi:app
}

main() {
    load_environment
    set_pythonpath
    start_server
}

main