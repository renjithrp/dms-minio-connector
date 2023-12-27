#!/bin/bash
export PYTHONPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$(dirname "$0")/src"
python -m unittest discover -s tests