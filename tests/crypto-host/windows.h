/* SPDX-License-Identifier: GPL-2.0-or-later
 * Host test aliases only; never included in the kernel build. */
#pragma once
#ifdef _WIN32
#include <stdint.h>
#include <string.h>
#define bzero(p,n) memset((p),0,(n))
#define bcopy(s,d,n) memmove((d),(s),(n))
typedef uint8_t u_int8_t;
typedef uint16_t u_int16_t;
typedef uint32_t u_int32_t;
typedef uint64_t u_int64_t;
typedef unsigned int u_int;
typedef unsigned char u_char;
#endif
