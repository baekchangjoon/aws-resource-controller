#!/usr/bin/env bash
# Build the Lambda Ingest deploy zip.
#
# Uses pip's --platform manylinux2014_x86_64 + --python-version 3.13 +
# --only-binary=:all: so we resolve Linux wheels even when run on macOS.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$HERE/build"
DIST="$HERE/dist"
PY="${PYTHON_BIN:-$HERE/.venv/bin/python}"

rm -rf "$BUILD" "$DIST"
mkdir -p "$BUILD" "$DIST"

"$PY" -m pip install \
  --quiet \
  --platform manylinux2014_x86_64 \
  --target "$BUILD" \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: \
  -r "$HERE/requirements.txt"

# Copy source (handler.py and any siblings).
cp "$HERE/src/handler.py" "$BUILD/"

# Drop test/__pycache__ artifacts from the dep tree to slim the zip.
find "$BUILD" -name "__pycache__" -type d -exec rm -rf {} +
find "$BUILD" -name "*.pyc" -delete
find "$BUILD" -name "*.dist-info" -type d -exec rm -rf {} +
find "$BUILD" -name "tests" -type d -exec rm -rf {} +

cd "$BUILD"
zip -qr "$DIST/handler.zip" .
SIZE="$(du -h "$DIST/handler.zip" | cut -f1)"
echo "Built: $DIST/handler.zip ($SIZE)"
