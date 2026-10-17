#!/bin/bash
set -euo pipefail
SOURCE_APP=${1:?source app required}
DESTINATION=${2:?destination app path required}
if [[ ! -d "$SOURCE_APP/Contents" ]]; then
  echo "Built app is missing: $SOURCE_APP" >&2
  exit 2
fi
if [[ -e "$DESTINATION" ]]; then
  STAMP=$(date +%Y%m%d-%H%M%S)
  BACKUP="${DESTINATION%.app}.repackaged-backup-$STAMP.app"
  mv "$DESTINATION" "$BACKUP"
  echo "Preserved previous app: $BACKUP"
fi
ditto --norsrc --noextattr "$SOURCE_APP" "$DESTINATION"
codesign -d "$DESTINATION" >/dev/null
echo "Installed: $DESTINATION"
