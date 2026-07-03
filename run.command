#!/bin/zsh
# BrakeLab launcher — double-click in Finder, or run ./run.command in Terminal.
# Uses the system Python 3.9 (which has a working PySide6) and finds the code via src/.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
export PYTHONPATH="$DIR/src"
PY="/Library/Developer/CommandLineTools/usr/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"
exec "$PY" -m brakelab
