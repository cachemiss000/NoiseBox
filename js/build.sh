#!/usr/bin/env bash

function try() {
  "$@" || { echo "COMMAND: '$*' failed" ; exit 1; }
}

try node dist/schema/convertToTypescript.js --out=src/schema
try tsc --build
