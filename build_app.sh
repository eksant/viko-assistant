#!/bin/bash
# Build VIKO.app — run from project root
set -e

VENV=".venv/bin/pyinstaller"
DIST="dist/VIKO.app"
FRAMEWORK="$DIST/Contents/Frameworks/PyQt6/Qt6/lib/QtWebEngineCore.framework"

echo "==> Building VIKO.app..."
"$VENV" VIKO.spec --noconfirm

# Fix: PyInstaller places QtWebEngine files in Versions/Resources/ but
# symlinks (Helpers, Resources) resolve to Versions/A/. Copy to correct path.
echo "==> Fixing QtWebEngine paths..."
WRONG="$FRAMEWORK/Versions/Resources"
CORRECT="$FRAMEWORK/Versions/A"
if [ -d "$WRONG/Helpers" ] && [ ! -d "$CORRECT/Helpers" ]; then
    cp -R "$WRONG/Helpers" "$CORRECT/"
fi
if [ -d "$WRONG/Resources" ] && [ ! -d "$CORRECT/Resources" ]; then
    cp -R "$WRONG/Resources" "$CORRECT/"
fi

echo "==> Done: $DIST"
echo "    Open with: open $DIST"
