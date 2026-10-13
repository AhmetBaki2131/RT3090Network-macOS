#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
"${CC:-cc}" -std=c99 -fsanitize=address,undefined -Iinclude -c src/rt3090_core.c -o build/dma-core-host.o
"${CXX:-c++}" -std=c++14 -Wall -Wextra -fsanitize=address,undefined -Iinclude -Itests/dma-host -Ibuild/generated tests/test_dma_bridge.cpp build/dma-core-host.o -o build/test_dma_bridge
UBSAN_OPTIONS=halt_on_error=1 ./build/test_dma_bridge
