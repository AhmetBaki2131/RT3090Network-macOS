#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
sh scripts/build-network-macos.sh "$@"
python3 scripts/make-control-app.py
python3 scripts/make-test-package.py --bundle build/DerivedData/Build/Products/Debug/RT3090Network.kext
echo 'Test archive: build/RT3090Network-0.3.5-test.zip (not loaded or installed)'
