/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "rt3090_core.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    assert(rt_pci_is_target(0x1814,0x3090,0x103c,0x1453));
    assert(!rt_pci_is_target(0xffff,0xffff,0xffff,0xffff));
    assert(!rt_pci_is_target(0,0,0,0));
    assert(!rt_pci_is_target(0x1814,0x3091,0x103c,0x1453));
    assert(!rt_pci_is_target(0x1815,0x3090,0x103c,0x1453));
    assert(!rt_pci_is_target(0x1814,0x3090,0x103d,0x1453));
    assert(!rt_pci_is_target(0x1814,0x3090,0x103c,0x1454));
    puts("PASS: 7 PCI identity cases; no physical PCI device involved");
    return 0;
}
