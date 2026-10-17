#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
APP=${1:-$ROOT/build/理屏.app}
PLIST="$APP/Contents/Info.plist"
PYTHON="$APP/Contents/Resources/python/bin/python3"
BACKEND="$APP/Contents/Resources/backend"
[[ -x "$APP/Contents/MacOS/UnjiggleRebuilt" ]]
[[ -x "$PYTHON" ]]
[[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$PLIST")" == "app.liping.local" ]]
codesign --verify --deep --strict "$APP"
VERSION=$(PYTHONPATH="$BACKEND" "$PYTHON" -m unjiggle_rebuilt version)
STATUS=$(PYTHONPATH="$BACKEND" "$PYTHON" -m unjiggle_rebuilt status --demo)
DIAGNOSIS=$(PYTHONPATH="$BACKEND" "$PYTHON" -m unjiggle_rebuilt diagnose --demo)
PREVIEW=$(PYTHONPATH="$BACKEND" "$PYTHON" -m unjiggle_rebuilt preview --demo --preset minimal)
printf '%s\n%s\n%s\n%s\n' "$VERSION" "$STATUS" "$DIAGNOSIS" "$PREVIEW" | \
  /usr/bin/python3 -c 'import json,sys; rows=[json.loads(line) for line in sys.stdin if line.strip()]; assert len(rows)==4 and all(r["ok"] for r in rows); assert rows[2]["report"]["counts"]["apps"] > 20; assert rows[3]["before"]["counts"]["pages"] >= rows[3]["after"]["counts"]["pages"]'
if rg -l 'Contents/MacOS/Unjiggle$' "$APP/Contents" >/dev/null; then
  echo "Found an unexpected dependency on the inspected app" >&2
  exit 3
fi
echo "Verified native app, signature, packaged backend, demo analysis, and preview safeguards."
