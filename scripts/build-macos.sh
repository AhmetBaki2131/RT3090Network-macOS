#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ "$(uname -s)" != Darwin ]; then
    echo "A Mac with Xcode is required for the Xcode build and kext validation." >&2
    exit 1
fi
command -v xcodebuild >/dev/null
command -v python3 >/dev/null
if [ "$#" -gt 1 ]; then echo "Usage: $0 [path/to/rt2860.bin]" >&2; exit 1; fi
if [ "$#" -eq 1 ]; then
    python3 scripts/prepare_firmware.py --firmware "$1" --output build/generated/FirmwareData.h
else
    python3 scripts/prepare_firmware.py --output build/generated/FirmwareData.h
fi
# Kernel headers and x86_64 libkmod are included from the pinned MacKernelSDK.
# macOS SDK selection remains Xcode's installed SDK; deployment target=10.13.
xcodebuild -project RT3090.xcodeproj -scheme RT3090Diagnostic \
    -configuration Debug -derivedDataPath build/DerivedData \
    ARCHS=x86_64 ONLY_ACTIVE_ARCH=NO CODE_SIGNING_ALLOWED=NO build
KEXT_PATH=build/DerivedData/Build/Products/Debug/RT3090Diagnostic.kext
test -f "$KEXT_PATH/Contents/MacOS/RT3090Diagnostic"
plutil -lint "$KEXT_PATH/Contents/Info.plist"
file "$KEXT_PATH/Contents/MacOS/RT3090Diagnostic"
echo "Experimental bring-up artifact: $KEXT_PATH"
echo "Wi-Fi scanning, association and WPA2 are NOT implemented. Do not install for daily use."
echo "On the actual High Sierra target, run: sudo kextutil -n -t $KEXT_PATH"
