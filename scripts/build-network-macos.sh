#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ "$(uname -s)" != Darwin ]; then
    echo "A Mac with Xcode is required for the Xcode build and kext validation." >&2
    exit 1
fi
command -v xcodebuild >/dev/null
command -v python3 >/dev/null
xcrun --sdk macosx10.13 --show-sdk-path
if [ "$#" -gt 1 ]; then echo "Usage: $0 [path/to/rt2860.bin]" >&2; exit 1; fi
if [ "$#" -eq 1 ]; then
    python3 scripts/prepare_firmware.py --firmware "$1" --output build/generated/FirmwareData.h
else
    python3 scripts/prepare_firmware.py --firmware firmware/rt2860.bin --output build/generated/FirmwareData.h
fi
# Kernel headers and x86_64 libkmod are included from the pinned MacKernelSDK.
# The requested SDK must actually be installed: MacOSX10.13.sdk; deployment=10.13.
xcodebuild -project RT3090Network.xcodeproj -scheme RT3090Network \
    -sdk macosx10.13 -configuration Debug -derivedDataPath build/DerivedData \
    RT3090_NETWORK_ENABLED="${RT3090_NETWORK_ENABLED:-1}" ARCHS=x86_64 ONLY_ACTIVE_ARCH=NO CODE_SIGNING_ALLOWED=NO build
KEXT_PATH=build/DerivedData/Build/Products/Debug/RT3090Network.kext
test -f "$KEXT_PATH/Contents/MacOS/RT3090Network"
plutil -lint "$KEXT_PATH/Contents/Info.plist"
file "$KEXT_PATH/Contents/MacOS/RT3090Network"
echo "Experimental bring-up artifact: $KEXT_PATH"
echo "Network build by default; optional diagnostic build via RT3090_NETWORK_ENABLED=0. Hardware validation required."
printf 'On High Sierra, validate without loading: sudo kextutil -n -t "%s"\n' "$KEXT_PATH"
