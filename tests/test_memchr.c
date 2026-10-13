/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "rt3090_core.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    unsigned char a[] = {0xff, 1, 0, 2};
    assert(rt_memchr(NULL, 0, 0) == NULL);
    assert(rt_memchr(NULL, 0, 9) == NULL);
    assert(rt_memchr(a, 0, 0) == NULL);
    assert(rt_memchr(a, 0, 2) == NULL);
    assert(rt_memchr(a, 0, sizeof(a)) == a+2);
    assert(rt_memchr(a, -1, sizeof(a)) == a);
    assert(rt_memchr(a, 2, sizeof(a)) == a+3);
    assert(rt_memchr(a, 7, sizeof(a)) == NULL);
    assert(rt_memchr((void *)(UINTPTR_MAX-1), 0, 3) == NULL);
    assert(rt_memchr(a, 0, SIZE_MAX) == NULL);
    puts("PASS: 10 bounded-search assertions (ASan/UBSan)");
    return 0;
}
