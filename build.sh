#!/usr/bin/env bash

function try() {
  "$@" || { echo "COMMAND: '$*' failed" ; exit 1; }
}

# TODO: Come up with a better venv discovery method.
source venv/Scripts/activate

try python "./run.py" buildschema --out=./schema
try cd js
try ./build.sh
