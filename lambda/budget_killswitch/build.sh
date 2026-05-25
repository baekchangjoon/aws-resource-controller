#!/usr/bin/env bash
# Build the SES kill-switch Lambda deploy zip.
#
# boto3 is provided by the Lambda runtime, so this is just handler.py.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$HERE/build"
DIST="$HERE/dist"

rm -rf "$BUILD" "$DIST"
mkdir -p "$BUILD" "$DIST"

cp "$HERE/src/handler.py" "$BUILD/"

cd "$BUILD"
zip -qr "$DIST/handler.zip" .
SIZE="$(du -h "$DIST/handler.zip" | cut -f1)"
echo "Built: $DIST/handler.zip ($SIZE)"
