/* SPDX-License-Identifier: GPL-2.0-or-later */
#pragma once
#include <endian.h>
#define _OSSwapInt32(x) __builtin_bswap32(x)
#define _OSSwapInt64(x) __builtin_bswap64(x)
