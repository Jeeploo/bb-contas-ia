#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python -m app.start
fi
exec python -m app.start
