#!/bin/bash

set_pythonpath() {
    export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
}

run_unit_tests() {
    cd "$(dirname "$0")/src" || exit 1
    python -m unittest discover -s tests
}

main() {
    set_pythonpath
    run_unit_tests
}

main