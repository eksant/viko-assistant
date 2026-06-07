#!/usr/bin/env bash
# Build VIKO.app — run from project root: ./scripts/build.sh
set -euo pipefail

cd "$(dirname "$0")/.."

PYINSTALLER=".venv/bin/pyinstaller"
DIST="dist/VIKO.app"
FRAMEWORK="$DIST/Contents/Frameworks/PyQt6/Qt6/lib/QtWebEngineCore.framework"

# ── Lint ────────────────────────────────────────────────────────────────────
echo "[1/3] Linting..."
.venv/bin/ruff check viko/ viko.py --select F401,F811,F841 --output-format=concise

# ── PyInstaller build ────────────────────────────────────────────────────────
echo "[2/3] Building $DIST..."
"$PYINSTALLER" VIKO.spec --noconfirm

# ── Fix QtWebEngine paths ────────────────────────────────────────────────────
# PyInstaller copies WebEngine files to Versions/Resources/ but the framework
# symlinks (Helpers, Resources) resolve through Versions/A/. Copy to fix.
echo "[3/3] Fixing QtWebEngine paths..."
WRONG="$FRAMEWORK/Versions/Resources"
CORRECT="$FRAMEWORK/Versions/A"

if [ -d "$WRONG/Helpers" ] && [ ! -d "$CORRECT/Helpers" ]; then
    cp -R "$WRONG/Helpers" "$CORRECT/"
fi
if [ -d "$WRONG/Resources" ] && [ ! -d "$CORRECT/Resources" ]; then
    cp -R "$WRONG/Resources" "$CORRECT/"
fi

echo ""
echo "Done → $DIST"
echo "Run:   open $DIST"
echo "   or: ./scripts/start.sh --app"
