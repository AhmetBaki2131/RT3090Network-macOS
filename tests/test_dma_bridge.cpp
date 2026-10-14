/* SPDX-License-Identifier: GPL-2.0-or-later
 * Execute the real RTBSDGlue.cpp with a host-only IOKit shim. No physical DMA. */
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <cstdio>
#include <cerrno>
#include <cassert>
#include <algorithm>
#include "rt3090_core.h"
#ifdef _WIN32
using caddr_t=char*;
static void bzero(void *p,size_t n){std::memset(p,0,n);}
#endif
#define RTBSD_COMPAT_HPP
using UInt32=uint32_t; using UInt64=uint64_t; using IOReturn=int;
enum {kIOReturnSuccess=0,kIODirectionInOut=3,kIOMemoryPhysicallyContiguous=16};
static bool null_cpu=false;
static int prepared=0,completed=0; static uint64_t emitted_address=0x100000;
struct IOBufferMemoryDescriptor {
    unsigned char *bytes; size_t size;
    static IOBufferMemoryDescriptor *inTaskWithPhysicalMask(int,int,size_t n,uint64_t) {
        auto *p=new IOBufferMemoryDescriptor; p->bytes=(unsigned char*)std::malloc(n); p->size=n; return p;
    }
    size_t getLength() {return size;} void *getBytesNoCopy(){return null_cpu?nullptr:bytes;}
    void release(){std::free(bytes); delete this;}
};
struct IODMACommand {
    enum {OutputHost32=0,kMapped=1};
    struct Segment32 {uint32_t fIOVMAddr,fLength;}; IOBufferMemoryDescriptor *m=nullptr;
    static IODMACommand *withSpecification(int,int,size_t,int,size_t,int){return new IODMACommand;}
    int setMemoryDescriptor(IOBufferMemoryDescriptor *p){m=p; prepared++; return 0;}
    int clearMemoryDescriptor(){if(m){completed++;m=nullptr;}return 0;}
    int gen32IOVMSegments(UInt64 *off,Segment32 *s,UInt32 *n){*off=m->size;*n=1;s->fIOVMAddr=emitted_address;s->fLength=m->size;return 0;}
    void release(){delete this;}
};
struct IOMemoryMap {size_t length=0x8000;size_t getLength(){return length;}};
struct IOWorkLoop {bool gated=false;bool inGate(){return gated;}};
IOWorkLoop *_fWorkloop=nullptr;
static int kernel_task=0;
static void *IOMalloc(size_t n){return std::malloc(n);} static void IOFree(void*p,size_t){std::free(p);}
static void IOLog(const char*,...) {} static void OSSynchronizeIO(){}
static uint32_t OSReadLittleInt32(volatile uint8_t *p,unsigned o){uint32_t n;std::memcpy(&n,(const void*)(p+o),4);return n;}
static void OSWriteLittleInt32(volatile uint8_t*p,unsigned o,uint32_t n){std::memcpy((void*)(p+o),&n,4);}
struct packet {unsigned char *data;size_t len,total;packet *next;};using mbuf_t=packet*;
static size_t mbuf_pkthdr_len(mbuf_t p){return p->total;} static size_t mbuf_len(mbuf_t p){return p->len;} static mbuf_t mbuf_next(mbuf_t p){return p->next;}
static int mbuf_copydata(mbuf_t p,size_t off,size_t n,void *dst){
    auto *out=(unsigned char*)dst;
    while(p&&off>=p->len){off-=p->len;p=p->next;}
    while(p&&n){size_t take=std::min(n,p->len-off);std::memcpy(out,p->data+off,take);out+=take;n-=take;off=0;p=p->next;}
    return n?EINVAL:0;
}
using bus_dma_tag_t=unsigned;using bus_size_t=uint32_t;using bus_addr_t=uint64_t;
using bus_space_tag_t=IOMemoryMap*;using bus_space_handle_t=volatile uint8_t*;
struct bus_dma_segment {uint64_t ds_addr,ds_len;IOBufferMemoryDescriptor *memory;};using bus_dma_segment_t=bus_dma_segment;
struct bus_dmamap {IODMACommand *command;IOBufferMemoryDescriptor *memory;void *cpu_buffer;mbuf_t packet;uint64_t dma_address;bool loaded;uint64_t dm_mapsize;int dm_nsegs;unsigned max_segments,max_size,max_segment_size;bus_dma_segment_t dm_segs[15];};using bus_dmamap_t=bus_dmamap*;
struct device{};
enum {BUS_DMASYNC_PREREAD,BUS_DMASYNC_PREWRITE,BUS_DMASYNC_POSTREAD,BUS_DMASYNC_POSTWRITE};
static void *firmware_malloc(size_t n){return std::malloc(n);}
#define malloc(n,a,b) firmware_malloc(n)
#include "../port/RTBSDGlue.cpp"
#undef malloc
int main(){
    IOWorkLoop loop;_fWorkloop=&loop;bus_dmamap_t m=nullptr;
    assert(bus_dmamap_create(0,64,1,64,0,0,&m)==0);assert(prepared==1&&completed==0);
    unsigned char cpu[64]={};cpu[3]=42;loop.gated=true;
    assert(bus_dmamap_load(0,m,cpu,64,nullptr,0)==0);
    bus_dmamap_sync(0,m,3,1,BUS_DMASYNC_PREWRITE);assert(((unsigned char*)m->memory->getBytesNoCopy())[3]==42);
    ((unsigned char*)m->memory->getBytesNoCopy())[5]=91;
    bus_dmamap_sync(0,m,5,1,BUS_DMASYNC_POSTREAD);assert(cpu[5]==91);
    assert(bus_dmamap_load(0,m,cpu,64,nullptr,0)==EINVAL);
    bus_dmamap_unload(0,m);assert(prepared==1&&completed==0);
    unsigned char a[]={1,2},b[]={3,4,5};packet tail{b,3,0,nullptr},head{a,2,5,&tail};
    assert(bus_dmamap_load_mbuf(0,m,&head,0)==0);bus_dmamap_sync(0,m,0,5,BUS_DMASYNC_PREWRITE);
    assert(std::memcmp(m->memory->getBytesNoCopy(),"\1\2\3\4\5",5)==0);
    bus_dmamap_sync(0,m,4,2,BUS_DMASYNC_PREWRITE);assert(rtbsd_dma_failed());rtbsd_dma_clear_failure();
    bus_dmamap_unload(0,m);head.total=6;assert(bus_dmamap_load_mbuf(0,m,&head,0)==EINVAL);
    packet cycle{nullptr,0,1,nullptr};cycle.next=&cycle;
    assert(bus_dmamap_load_mbuf(0,m,&cycle,0)==EINVAL);
    bus_dmamap_t denied=nullptr;assert(bus_dmamap_create(0,64,1,64,0,0,&denied)==EWOULDBLOCK);
    assert(prepared==1&&completed==0);loop.gated=false;bus_dmamap_destroy(0,m);assert(completed==1);
    emitted_address=0xfffffff0u;assert(bus_dmamap_create(0,64,1,64,0,0,&denied)!=0);
    null_cpu=true;assert(bus_dmamap_create(0,64,1,64,0,0,&denied)!=0);bus_dma_segment_t nullseg{};int actual=0;
    assert(bus_dmamem_alloc(0,64,16,0,&nullseg,1,&actual,0)==ENOMEM && !nullseg.memory);null_cpu=false;
    rtbsd_dma_clear_failure();IOMemoryMap map;
    bus_space_write_region_1(&map,nullptr,0,a,sizeof(a));assert(rtbsd_dma_failed());
    rtbsd_dma_clear_failure();bus_space_set_region_4(&map,nullptr,0,0,1);assert(rtbsd_dma_failed());
    unsigned char bar[0x8000]={};
    rtbsd_dma_clear_failure();bus_space_write_4(&map,bar,0x100,0x12345678);
    assert(!rtbsd_dma_failed() && bus_space_read_4(&map,bar,0x100)==0x12345678);
    for(unsigned off : {1u,0x7ffdu,0x8000u,0xfffffffcu}) {
        rtbsd_dma_clear_failure();assert(bus_space_read_4(&map,bar,off)==0xffffffffu && rtbsd_dma_failed());
        rtbsd_dma_clear_failure();bus_space_write_4(&map,bar,off,0);assert(rtbsd_dma_failed());
    }
    rtbsd_dma_clear_failure();assert(bus_space_read_4(nullptr,bar,0)==0xffffffffu && rtbsd_dma_failed());
    rtbsd_dma_clear_failure();bus_space_write_4(&map,nullptr,0,0);assert(rtbsd_dma_failed());
    map.length=4;rtbsd_dma_clear_failure();bus_space_write_4(&map,bar,0,0);assert(rtbsd_dma_failed());
    puts("PASS: real DMA bridge host-shim lifecycle, scatter-copy, invalid range, gate refusal and 4GiB overflow, null CPU allocation, null MMIO and cyclic chain checks; no physical DMA");
}
