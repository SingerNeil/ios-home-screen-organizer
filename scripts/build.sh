#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUTPUT_APP=${1:-$ROOT/build/Unjiggle Rebuilt.app}
OUTPUT_PARENT=$(dirname "$OUTPUT_APP")
mkdir -p "$OUTPUT_PARENT"
STAGE=$(mktemp -d "$OUTPUT_PARENT/.unjiggle-source-build.XXXXXX")
APP="$STAGE/Unjiggle Rebuilt.app"
trap 'chmod -R u+w "$STAGE" 2>/dev/null || true; rm -rf "$STAGE"' EXIT
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
xcrun swiftc -parse-as-library -framework SwiftUI -framework AppKit -target arm64-apple-macos14.0 \
  "$ROOT/Sources/UnjiggleRebuilt/App.swift" -o "$APP/Contents/MacOS/UnjiggleRebuilt"
cp "$ROOT/config/Info.plist" "$APP/Contents/Info.plist"
ditto --norsrc --noextattr "$ROOT/backend" "$APP/Contents/Resources/backend"
ditto --norsrc --noextattr "$ROOT/.venv" "$APP/Contents/Resources/python"
rm -rf "$APP/Contents/Resources/python/lib/python3.12/site-packages/pip" \
  "$APP/Contents/Resources/python/lib/python3.12/site-packages/pip-"*.dist-info 2>/dev/null || true
plutil -lint "$APP/Contents/Info.plist" >/dev/null
codesign --force --deep --sign - --timestamp=none "$APP"
codesign --verify --deep --strict "$APP"
if [[ -e "$OUTPUT_APP" ]]; then
  PREVIOUS="$OUTPUT_PARENT/Unjiggle Rebuilt.previous.app"
  [[ ! -e "$PREVIOUS" ]] || rm -rf "$PREVIOUS"
  mv "$OUTPUT_APP" "$PREVIOUS"
fi
mv "$APP" "$OUTPUT_APP"
echo "Built from source: $OUTPUT_APP"
