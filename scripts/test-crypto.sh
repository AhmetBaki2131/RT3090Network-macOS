#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p build
"${CC:-cc}" -std=c99 -D_DEFAULT_SOURCE -O1 -g -ffunction-sections -fdata-sections \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -Itests/crypto-host -Ivendor/itl80211/openbsd -include tests/crypto-host/windows.h \
    tests/test_crypto.c vendor/itl80211/openbsd/crypto/sha1.c \
    vendor/itl80211/openbsd/crypto/sha1-pbkdf2.c \
    vendor/itl80211/openbsd/crypto/hmac.c vendor/itl80211/openbsd/crypto/sha2.c port/rijndael.c \
    -Wl,--gc-sections -o build/test_crypto
UBSAN_OPTIONS=halt_on_error=1 ./build/test_crypto
