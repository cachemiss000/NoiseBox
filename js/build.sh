#!/usr/bin/env bash

function try() {
  $* || { echo "COMMAND: '$*' failed" ; exit 1; }
}

try tsc --build
try node dist/schema/convertToTypescript.js --out=src/schema
