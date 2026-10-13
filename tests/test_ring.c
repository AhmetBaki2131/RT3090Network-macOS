/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "rt3090_core.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    uint32_t distance=999;
    assert(rt_ring_distance(0,0,0,&distance)==RT_INVALID);
    assert(rt_ring_distance(64,0,64,&distance)==RT_INVALID);
    assert(rt_ring_distance(0,128,128,&distance)==RT_INVALID);
    assert(rt_ring_distance(0,UINT32_MAX,64,&distance)==RT_INVALID);
    assert(rt_ring_distance(0,1,64,NULL)==RT_INVALID);
    assert(distance==999);
    for (uint32_t size=64;size<=128;size*=2)
        for (uint32_t first=0;first<size;first++)
            for (uint32_t end=0;end<size;end++) {
                uint32_t cursor=first,steps=0;
                while(cursor!=end) { cursor=(cursor+1)%size; steps++; }
                assert(rt_ring_distance(first,end,size,&distance)==RT_OK);
                assert(distance==steps);
            }
    puts("PASS: 20480 ring pairs, 5 invalid inputs, unchanged output on failure; ASan/UBSan");
    return 0;
}
