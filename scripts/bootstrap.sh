#!/bin/bash
set -euo pipefail
PYTHON=${1:-/opt/homebrew/bin/python3.12}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
VENV="$ROOT/.venv"
if [[ ! -x "$PYTHON" ]]; then
  echo "Python 3.12 was not found at: $PYTHON" >&2
  exit 2
fi
if [[ ! -x "$VENV/bin/python3" ]]; then
  "$PYTHON" -m venv --copies "$VENV"
fi
"$VENV/bin/python3" -m pip install --disable-pip-version-check -q -r "$ROOT/requirements.txt"
"$VENV/bin/python3" -c 'import pymobiledevice3' >/dev/null
echo "Device runtime ready: $VENV"
