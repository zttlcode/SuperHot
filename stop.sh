#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
runtime_directory="${SUPERHOT_RUNTIME:-.runtime}"
if [ -f "$runtime_directory/launcher.heartbeat" ]; then
  touch "$runtime_directory/stop.request"
  printf '%s\n' 'Stop requested.'
else
  printf '%s\n' 'SuperHot is not running.'
fi
