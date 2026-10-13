/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RT3090_DIAGNOSTIC_HPP
#define RT3090_DIAGNOSTIC_HPP
#include <IOKit/IOService.h>
#include <IOKit/pci/IOPCIDevice.h>
#include <IOKit/IOMemoryDescriptor.h>
#include "rt3090_core.h"
/* Hardware bring-up target only. Deliberately has no network interface,
 * scan/associate entry points, or success responses for missing Wi-Fi. */
class RT3090Diagnostic : public IOService {
    OSDeclareDefaultStructors(RT3090Diagnostic)
public:
    IOService *probe(IOService *, SInt32 *) override;
    bool start(IOService *) override;
    void stop(IOService *) override;
    void free() override;
private:
    IOPCIDevice *pci=nullptr;
    IOMemoryMap *bar=nullptr;
    volatile uint8_t *registers=nullptr;
    IOByteCount registerLength=0;
    bool opened=false, changedMemoryEnable=false, firmwareAttempted=false;
    bool oldMemoryEnable=false;
    struct rt_bus bus={};
    static uint32_t read32(void *, uint32_t);
    static void write32(void *, uint32_t, uint32_t);
    static void delay(void *, uint32_t);
    void cleanup();
    IOReturn testDmaMapping();
};
#endif
