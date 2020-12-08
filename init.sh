#!/usr/bin/env bash

function try() {
  $* || { echo "COMMAND: '$*' failed" ; exit 1; }
}

ENV=$1
if [ -z "$ENV" ]; then
  ENV="venv"
  echo "Defaulting to virtual environment name venv"
fi

if  ! virtualenv -h &> /dev/null; then
  echo "Required binary 'virtualenv' not installed. trying to install now..."
  try python -m pip install virtualenv --no-input
fi

try virtualenv $ENV
try source $ENV/Scripts/activate
pip install -r requirements.txt
