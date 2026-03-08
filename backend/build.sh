#!/usr/bin/env bash
# Render build script — runs from backend/ (Render root directory)
# Builds the React frontend then installs Python deps

set -e

echo "==> Building React frontend..."
cd "$(dirname "$0")/../frontend"
npm install
npm run build
echo "==> React build complete. dist/ contents:"
ls dist/

echo "==> Installing Python dependencies..."
cd "$(dirname "$0")"
pip install -r requirements.txt

echo "==> Build complete."
