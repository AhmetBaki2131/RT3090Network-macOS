#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -z "${ZIG:-}" ]; then
    echo "Set ZIG to the path of Zig 0.13.0. This compiles Mach-O objects only." >&2
    exit 1
fi
mkdir -p build/cross build/generated
# Do not overwrite a firmware include selected by a prior macOS build.
if [ ! -f build/generated/FirmwareData.h ]; then
    python3 scripts/prepare_firmware.py --output build/generated/FirmwareData.h
fi
export ZIG_GLOBAL_CACHE_DIR="$(pwd)/build/zig-cache"
"$ZIG" cc -target x86_64-macos.10.13 -std=c99 -mkernel \
    -fno-stack-protector -ffreestanding -fno-builtin -mno-red-zone \
    -mno-sse -mno-sse2 -mno-mmx -nostdinc -DKERNEL -DKERNEL_PRIVATE -DDRIVER_PRIVATE \
    -Ivendor/MacKernelSDK/Headers -Iinclude -Wall -Wextra -Werror \
    -c src/rt3090_core.c -o build/cross/rt3090_core.o
"$ZIG" c++ -target x86_64-macos.10.13 -std=c++11 -mkernel -fapple-kext \
    -fno-exceptions -fno-rtti -fno-stack-protector \
    -fno-register-global-dtors-with-atexit -ffreestanding -fno-builtin \
    -mllvm -disable-atexit-based-global-dtor-lowering \
    -mno-red-zone -mno-sse -mno-sse2 -mno-mmx -nostdinc \
    -DKERNEL -DKERNEL_PRIVATE -DDRIVER_PRIVATE \
    -Ivendor/MacKernelSDK/Headers -Iinclude -Ikext -Ibuild/generated \
    -Wall -Wextra -Werror -Wno-unused-parameter -Wno-deprecated-declarations \
    -c kext/RT3090Diagnostic.cpp -o build/cross/RT3090Diagnostic.o
file build/cross/rt3090_core.o build/cross/RT3090Diagnostic.o
echo "Mach-O object compilation passed. This step does not link or load-test a kext."
