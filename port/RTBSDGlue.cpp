/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "RTBSDCompat.hpp"
#include "rt3090_core.h"
#include "FirmwareData.h"
#include <IOKit/IOWorkLoop.h>
extern IOWorkLoop *_fWorkloop;
static bool dma_failed=false;
bool rtbsd_dma_failed() { return dma_failed; }
void rtbsd_dma_clear_failure() { dma_failed=false; }

uint32_t bus_space_read_4(bus_space_tag_t map,bus_space_handle_t base,bus_size_t off)
{
    if(!map||!base||(off&3)||off>map->getLength()||map->getLength()-off<4) { dma_failed=true; return 0xffffffffu; }
    uint32_t value=OSReadLittleInt32(base,off); OSSynchronizeIO(); return value;
}
void bus_space_write_4(bus_space_tag_t map,bus_space_handle_t base,bus_size_t off,uint32_t value)
{
    if(!map||!base||(off&3)||off>map->getLength()||map->getLength()-off<4 || map->getLength()<RT_MAC_CSR0+4) { dma_failed=true; return; }
    OSWriteLittleInt32(base,off,value); OSSynchronizeIO();
    (void)OSReadLittleInt32(base,RT_MAC_CSR0); OSSynchronizeIO();
}
void bus_space_barrier(bus_space_tag_t,bus_space_handle_t,bus_size_t,bus_size_t,int) { OSSynchronizeIO(); }
void bus_space_write_region_1(bus_space_tag_t map,bus_space_handle_t base,bus_size_t off,const uint8_t *p,size_t n)
{
    if(!map||!base||!p||off>map->getLength()||n>map->getLength()-off) { dma_failed=true; return; }
    size_t i;
    /* Hardware SRAM tables may contain arbitrary lengths. Use byte writes
     * for the OpenBSD-style hardware backend firmware/table writes. */
    for(i=0;i<n;i++) base[off+i]=p[i];
    OSSynchronizeIO(); (void)bus_space_read_4(map,base,RT_MAC_CSR0);
}
void bus_space_set_region_4(bus_space_tag_t map,bus_space_handle_t base,bus_size_t off,uint32_t value,size_t words)
{
    if(!map||!base||(off&3)||off>map->getLength()||words>(map->getLength()-off)/4) { dma_failed=true; return; }
    for(size_t i=0;i<words;i++) bus_space_write_4(map,base,off+(uint32_t)(i*4),value);
}
int bus_dmamap_create(bus_dma_tag_t,bus_size_t size,int count,bus_size_t maxsegment,bus_size_t boundary,int,bus_dmamap_t *out)
{
    if(!out||!size||count<1||count>15||!maxsegment||boundary||size>maxsegment) return EINVAL;
    if(_fWorkloop && _fWorkloop->inGate()) return EWOULDBLOCK;
    bus_dmamap_t m=(bus_dmamap_t)IOMalloc(sizeof(*m));
    if(!m) return ENOMEM;
    bzero(m,sizeof(*m)); m->max_segments=count; m->max_size=size; m->max_segment_size=maxsegment;
    // Prepare once outside the gate. Runtime packets copy through this pinned
    // physically contiguous <4GiB buffer; they never prepare/complete a map.
    m->memory=IOBufferMemoryDescriptor::inTaskWithPhysicalMask(kernel_task,
        kIODirectionInOut|kIOMemoryPhysicallyContiguous,size,0xfffff000ULL);
    m->command=IODMACommand::withSpecification(IODMACommand::OutputHost32,32,maxsegment,IODMACommand::kMapped,size,1);
    if(!m->memory || !m->command || !m->memory->getBytesNoCopy()) goto fail;
    if(m->command->setMemoryDescriptor(m->memory)!=kIOReturnSuccess) goto fail;
    {
        IODMACommand::Segment32 segment; UInt32 n=1; UInt64 offset=0;
        if(m->command->gen32IOVMSegments(&offset,&segment,&n)!=kIOReturnSuccess || n!=1 || offset!=size ||
           segment.fLength!=size || (uint64_t)segment.fIOVMAddr+size>0x100000000ULL) goto fail;
        m->dma_address=segment.fIOVMAddr;
    }
    bzero(m->memory->getBytesNoCopy(),size); *out=m; return 0;
fail:
    if(m->command) { m->command->clearMemoryDescriptor(); m->command->release(); }
    if(m->memory) m->memory->release();
    IOFree(m,sizeof(*m)); return ENOMEM;
}
void bus_dmamap_unload(bus_dma_tag_t,bus_dmamap_t m)
{
    if(!m) return;
    m->cpu_buffer=nullptr; m->packet=nullptr; m->loaded=false;
    m->dm_nsegs=0; m->dm_mapsize=0;
}
void bus_dmamap_destroy(bus_dma_tag_t tag,bus_dmamap_t m)
{
    if(!m) return;
    if(_fWorkloop && _fWorkloop->inGate()) {
        dma_failed=true; IOLog("RT3090: refusing gated DMA destruction; memory retained\n"); return;
    }
    bus_dmamap_unload(tag,m); m->command->clearMemoryDescriptor();
    m->command->release(); m->memory->release(); IOFree(m,sizeof(*m));
}
int bus_dmamem_alloc(bus_dma_tag_t,bus_size_t size,bus_size_t align,bus_size_t boundary,bus_dma_segment_t *seg,int n,int *actual,int)
{
    if(!seg||n!=1||!actual||!size||boundary||!align||(align&(align-1))) return EINVAL;
    /* Rings must remain coherent rather than use DMA bounce copies. Allocate
     * backing memory below 4 GiB; still use IODMACommand for IOVM addresses. */
    seg->memory=IOBufferMemoryDescriptor::inTaskWithPhysicalMask(kernel_task,
        kIODirectionInOut|kIOMemoryPhysicallyContiguous,size,0xffffffffULL & ~((uint64_t)align-1));
    if(!seg->memory) return ENOMEM;
    if(!seg->memory->getBytesNoCopy()) { seg->memory->release(); seg->memory=nullptr; return ENOMEM; }
    bzero(seg->memory->getBytesNoCopy(),size); seg->ds_addr=0; seg->ds_len=size; *actual=1; return 0;
}
int bus_dmamem_map(bus_dma_tag_t,bus_dma_segment_t *seg,int count,size_t n,caddr_t *out,int)
{
    if(!seg||count!=1||!seg->memory||!out||n>seg->memory->getLength()) return EINVAL;
    *out=(caddr_t)seg->memory->getBytesNoCopy(); return *out?0:ENOMEM;
}
void bus_dmamem_unmap(bus_dma_tag_t,caddr_t,size_t)
{
    /* map returned the allocation's existing kernel pointer, not a separately
     * retained IOMemoryMap. The allocation is released by dmamem_free. */
}
void bus_dmamem_free(bus_dma_tag_t,bus_dma_segment_t *seg,int count)
{
    if(!seg||count!=1) return;
    if(seg->memory) { seg->memory->release(); seg->memory=nullptr; }
    seg->ds_addr=0; seg->ds_len=0;
}
static int activate_map(bus_dmamap_t m,size_t size)
{
    if(!m||!m->memory||!size||size>m->max_size||m->loaded) return EINVAL;
    m->dm_segs[0].ds_addr=m->dma_address; m->dm_segs[0].ds_len=size;
    m->dm_nsegs=1; m->dm_mapsize=size; m->loaded=true; return 0;
}
int bus_dmamap_load(bus_dma_tag_t,bus_dmamap_t m,void *p,bus_size_t size,void *,int)
{
    if(!p) return EINVAL;
    int error=activate_map(m,size); if(!error) m->cpu_buffer=p; return error;
}
int bus_dmamap_load_mbuf(bus_dma_tag_t,bus_dmamap_t m,mbuf_t packet,int)
{
    if(!packet||!m) return EINVAL;
    size_t size=mbuf_pkthdr_len(packet),total=0;
    if(!size || size>m->max_size) return EINVAL;
    unsigned walked=0;
    for(mbuf_t p=packet;p;p=mbuf_next(p)) {
        if(++walked>256) return EINVAL; // reject cyclic/invalid zero-length chains
        size_t length=mbuf_len(p);
        if(total>size || length>size-total) return EINVAL;
        total+=length;
    }
    if(total!=size) return EINVAL;
    int error=activate_map(m,size); if(!error) m->packet=packet; return error;
}
void bus_dmamap_sync(bus_dma_tag_t,bus_dmamap_t m,bus_addr_t off,bus_size_t len,int op)
{
    if(m&&!m->loaded&&!len&&!off) return;
    if(!m||!m->loaded||off>m->dm_mapsize||len>m->dm_mapsize-off) {
        dma_failed=true; IOLog("RT3090: invalid DMA sync rejected\n"); return;
    }
    uint8_t *bounce=(uint8_t *)m->memory->getBytesNoCopy()+off;
    OSSynchronizeIO();
    if(op==BUS_DMASYNC_PREWRITE) {
        if(m->packet) { if(mbuf_copydata(m->packet,off,len,bounce)) dma_failed=true; }
        else if(m->cpu_buffer) memcpy(bounce,(uint8_t *)m->cpu_buffer+off,len);
        else dma_failed=true;
    } else if(op==BUS_DMASYNC_POSTREAD) {
        if(m->cpu_buffer) memcpy((uint8_t *)m->cpu_buffer+off,bounce,len);
        else dma_failed=true; // RX uses contiguous CPU buffers, never packet chains.
    }
    OSSynchronizeIO();
}
void config_mountroot(void *object,void (*fn)(struct device *)) { fn((struct device *)object); }
int loadfirmware(const char *name,uint8_t **out,size_t *length)
{
    if(!name||!out||!length||strcmp(name,"ral-rt2860")) return ENOENT;
#if RT3090_HAS_FIRMWARE
    if(rt_check_firmware(rt3090_firmware,sizeof(rt3090_firmware))) return EINVAL;
    *out=(uint8_t *)malloc(sizeof(rt3090_firmware),0,0);
    if(!*out) return ENOMEM;
    memcpy(*out,rt3090_firmware,sizeof(rt3090_firmware)); *length=sizeof(rt3090_firmware); return 0;
#else
    return ENOENT;
#endif
}
