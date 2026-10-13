/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "RT3090Diagnostic.hpp"
#include <IOKit/IOLib.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IODMACommand.h>
#include <libkern/OSByteOrder.h>
#include <pexpert/pexpert.h>
#include "FirmwareData.h"
#define super IOService
OSDefineMetaClassAndStructors(RT3090Diagnostic, IOService)

IOService *RT3090Diagnostic::probe(IOService *provider, SInt32 *score)
{
    IOPCIDevice *device=OSDynamicCast(IOPCIDevice,provider);
    int optIn=0;
    if(!PE_parse_boot_argn("-rt3090-lab",&optIn,sizeof(optIn))) return nullptr;
    if(!device || device->configRead16(kIOPCIConfigVendorID)!=0x1814 ||
       device->configRead16(kIOPCIConfigDeviceID)!=0x3090) return nullptr;
    return super::probe(provider,score);
}
uint32_t RT3090Diagnostic::read32(void *context,uint32_t offset)
{
    RT3090Diagnostic *self=static_cast<RT3090Diagnostic *>(context);
    if(!self->registers || (offset&3) || offset>self->registerLength ||
       self->registerLength-offset<4) return 0xffffffffu;
    uint32_t value=OSReadLittleInt32(self->registers,offset);
    OSSynchronizeIO();
    return value;
}
void RT3090Diagnostic::write32(void *context,uint32_t offset,uint32_t value)
{
    RT3090Diagnostic *self=static_cast<RT3090Diagnostic *>(context);
    if(!self->registers || (offset&3) || offset>self->registerLength ||
       self->registerLength-offset<4) return;
    OSWriteLittleInt32(self->registers,offset,value);
    OSSynchronizeIO();
    /* PCIe writes are posted; flush using a register without read side effects. */
    (void)OSReadLittleInt32(self->registers,RT_MAC_CSR0);
    OSSynchronizeIO();
}
void RT3090Diagnostic::delay(void *,uint32_t us)
{
    if(us>=1000) IOSleep((us+999)/1000);
    else IODelay(us);
}
IOReturn RT3090Diagnostic::testDmaMapping()
{
    /* Validate a 32-bit DMA mapping, but never give the device its address.
     * No ring registers, bus-master enable or interrupt sources are used. */
    IOBufferMemoryDescriptor *memory=IOBufferMemoryDescriptor::inTaskWithOptions(
        kernel_task,kIODirectionInOut,4096,256);
    if(!memory) return kIOReturnNoMemory;
    IODMACommand *dma=IODMACommand::withSpecification(IODMACommand::OutputHost32,
        32,4096,IODMACommand::kMapped,4096,256);
    if(!dma) { memory->release(); return kIOReturnNoMemory; }
    IOReturn rc=dma->setMemoryDescriptor(memory);
    if(rc==kIOReturnSuccess) {
        IODMACommand::Segment32 segment={}; UInt64 offset=0; UInt32 count=1;
        rc=dma->gen32IOVMSegments(&offset,&segment,&count);
        if(rc==kIOReturnSuccess && (count!=1 || offset!=4096 ||
            segment.fLength!=4096 || (segment.fIOVMAddr&255) ||
            (UInt64)segment.fIOVMAddr+segment.fLength>0x100000000ULL)) rc=kIOReturnUnsupported;
        if(rc==kIOReturnSuccess) setProperty("RT3090DMAMappingValidated",true);
        IOReturn clear=dma->clearMemoryDescriptor();
        if(rc==kIOReturnSuccess) rc=clear;
    }
    dma->release(); memory->release(); return rc;
}
bool RT3090Diagnostic::start(IOService *provider)
{
    int enabled=0,fwEnabled=0; uint32_t chip=0; int rc;
    uint8_t eeprom[RT_EEPROM_SIZE]; struct rt_identity identity;
    if(!PE_parse_boot_argn("-rt3090-lab",&enabled,sizeof(enabled))) return false;
    if(!super::start(provider)) return false;
    pci=OSDynamicCast(IOPCIDevice,provider);
    if(!pci) goto fail;
    pci->retain();
    if(!pci->open(this)) goto fail;
    opened=true;
    if(pci->configRead16(kIOPCIConfigVendorID)!=0x1814 ||
       pci->configRead16(kIOPCIConfigDeviceID)!=0x3090) goto fail;
    oldMemoryEnable=(pci->configRead16(kIOPCIConfigCommand)&kIOPCICommandMemorySpace)!=0;
    if(!oldMemoryEnable) { pci->setMemoryEnable(true); changedMemoryEnable=true; }
    bar=pci->mapDeviceMemoryWithRegister(kIOPCIConfigBaseAddress0);
    if(!bar || bar->getLength()<0x8000) goto fail;
    registers=reinterpret_cast<volatile uint8_t *>(bar->getVirtualAddress());
    registerLength=bar->getLength();
    bus.context=this; bus.read32=read32; bus.write32=write32; bus.delay_us=delay;
    rc=rt_wait_chip(&bus,&chip);
    if(rc || (chip>>16)!=0x3090) { IOLog("RT3090: unsupported/unresponsive ASIC, rc=%d CSR=%08x\n",rc,chip); goto fail; }
    /* Do not interfere with an already running device/another driver. */
    if((read32(this,RT_WPDMA)&15) || read32(this,RT_INT_MASK)!=0) {
        IOLog("RT3090: DMA/IRQ already active; refusing bring-up\n"); goto fail;
    }
    setProperty("RT3090ASIC",chip,32);
    setProperty("RT3090SubsystemVendor",pci->configRead16(kIOPCIConfigSubSystemVendorID),16);
    setProperty("RT3090SubsystemID",pci->configRead16(kIOPCIConfigSubSystemID),16);
    rc=rt_read_eeprom(&bus,eeprom);
    if(rc) { IOLog("RT3090: EEPROM transport failure %d\n",rc); goto fail; }
    rc=rt_parse_eeprom(eeprom,sizeof(eeprom),&identity);
    if(rc) { IOLog("RT3090: invalid/unsupported EEPROM %d; no fabricated MAC\n",rc); goto fail; }
    setProperty("RT3090EEPROM",eeprom,sizeof(eeprom));
    setProperty("RT3090MAC",identity.mac,sizeof(identity.mac));
    setProperty("RT3090RFType",identity.rf_type,8);
    setProperty("RT3090TXChains",identity.tx_chains,8);
    setProperty("RT3090RXChains",identity.rx_chains,8);
    rc=testDmaMapping();
    setProperty("RT3090DMAMappingResult",(UInt32)rc,32);
    /* Mapping failure is recorded, not claimed as usable DMA. This target
     * only reads EEPROM; it does not require live DMA to remain attached. */
    if(PE_parse_boot_argn("-rt3090-fw",&fwEnabled,sizeof(fwEnabled))) {
#if RT3090_HAS_FIRMWARE
        firmwareAttempted=true;
        rc=rt_boot_firmware(&bus,rt3090_firmware,sizeof(rt3090_firmware));
        if(rc) { IOLog("RT3090: MCU firmware boot failed %d\n",rc); goto fail; }
        setProperty("RT3090FirmwareBooted",true);
#else
        IOLog("RT3090: -rt3090-fw requested but no firmware was supplied at build time\n"); goto fail;
#endif
    }
    setProperty("RT3090Status","Experimental EEPROM/firmware bring-up; Wi-Fi not implemented");
    setProperty("RT3090WiFiImplemented",false);
    IOLog("RT3090: EEPROM read complete. No scanning, association or network interface.\n");
    registerService();
    return true;
fail:
    cleanup(); super::stop(provider); return false;
}
void RT3090Diagnostic::cleanup()
{
    if(firmwareAttempted && registers) {
        int rc=rt_quiesce(&bus);
        if(rc) IOLog("RT3090: cleanup quiesce failed %d; cold reboot required\n",rc);
        firmwareAttempted=false;
    }
    registers=nullptr; registerLength=0;
    if(bar) { bar->release(); bar=nullptr; }
    if(pci) {
        if(changedMemoryEnable) { pci->setMemoryEnable(oldMemoryEnable); changedMemoryEnable=false; }
        if(opened) { pci->close(this); opened=false; }
        pci->release(); pci=nullptr;
    }
}
void RT3090Diagnostic::stop(IOService *provider) { cleanup(); super::stop(provider); }
void RT3090Diagnostic::free() { cleanup(); super::free(); }
