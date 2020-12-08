#!/usr/bin/env bash

function try() {
  $* || { echo "COMMAND: '$*' failed" ; exit 1; }
}

try python "./run.py" buildschema --out=./schema
cd js
try ./build.sh
