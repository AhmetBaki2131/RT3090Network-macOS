#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
"${CC:-cc}" -std=c99 -Wall -Wextra -Werror -fsanitize=address,undefined -Iinclude src/rt3090_core.c tests/test_pci.c -o build/test_pci
UBSAN_OPTIONS=halt_on_error=1 ./build/test_pci
