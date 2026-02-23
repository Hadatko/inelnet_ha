#!/usr/bin/env bash
# Build and upload inelnet-api package to PyPI.
# Uses .env.pypi (TWINE_USERNAME, TWINE_PASSWORD) if present.
set -e
cd "$(dirname "$0")/.."

if [ -f .env.pypi ]; then
  set -a
  source .env.pypi
  set +a
fi

# Always clean, then build (avoids uploading old versions from dist/)
rm -rf dist/ build/ inelnet_api.egg-info/
python3 -m build
twine upload dist/*
