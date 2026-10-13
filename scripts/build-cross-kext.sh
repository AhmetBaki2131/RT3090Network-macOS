#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -z "${ZIG:-}" ] || [ -z "${LD64:-}" ]; then
    echo "Set ZIG=Zig-0.13.0-executable and LD64=cctools-port-ld64-executable." >&2
    exit 1
fi
# Rebuild without firmware: this distributed artifact only probes EEPROM.
# Both compiler and linker are real Mach-O tools; no binary header patching.
python3 scripts/prepare_firmware.py --output build/generated/FirmwareData.h
sh scripts/check-cross.sh
export ZIG_GLOBAL_CACHE_DIR="$(pwd)/build/zig-cache"
"$ZIG" cc -target x86_64-macos.10.13 -std=c99 -mkernel \
    -fno-stack-protector -ffreestanding -fno-builtin -mno-red-zone \
    -mno-sse -mno-sse2 -mno-mmx -nostdinc -DKERNEL -DKERNEL_PRIVATE -DDRIVER_PRIVATE \
    -Ivendor/MacKernelSDK/Headers -Iinclude \
    -c cross/KmodInfo.c -o build/cross/KmodInfo.o
mkdir -p build/cross/RT3090Diagnostic.kext/Contents/MacOS
cp Info.plist build/cross/RT3090Diagnostic.kext/Contents/Info.plist
"$LD64" -arch x86_64 -macosx_version_min 10.13 -kext -undefined dynamic_lookup \
    build/cross/RT3090Diagnostic.o build/cross/rt3090_core.o build/cross/KmodInfo.o \
    vendor/MacKernelSDK/Library/x86_64/libkmod.a \
    -o build/cross/RT3090Diagnostic.kext/Contents/MacOS/RT3090Diagnostic
python3 scripts/verify_kext.py build/cross/RT3090Diagnostic.kext > build/cross/kext-structure.json
file build/cross/RT3090Diagnostic.kext/Contents/MacOS/RT3090Diagnostic
echo "Cross-linked laboratory kext only: no Wi-Fi, no macOS load test, no signature."
