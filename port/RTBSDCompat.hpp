/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RTBSD_COMPAT_HPP
#define RTBSD_COMPAT_HPP
#include <IOKit/network/IOEthernetController.h>
#include <IOKit/pci/IOPCIDevice.h>
#include <IOKit/IOBufferMemoryDescriptor.h>
#include <IOKit/IODMACommand.h>
#include <net80211/ieee80211_var.h>
#include <net80211/ieee80211_amrr.h>
#include <net80211/ieee80211_radiotap.h>
#include <sys/_mbuf.h>
#include <sys/pcireg.h>
#include <libkern/OSByteOrder.h>
#define NBPFILTER 0
#define	PCI_PRODUCT_RALINK_RT3290	0x3290		/* RT3290 */
#define	PCI_PRODUCT_RALINK_RT2890	0x0681		/* RT2890 */
#define	PCI_PRODUCT_RALINK_RT2790	0x0781		/* RT2790 */
#define	PCI_PRODUCT_AWT_RT2890	0x1059		/* RT2890 */
#define BUS_DMA_NOWAIT 0
#define BUS_DMA_ZERO 0
#define BUS_DMA_READ 0
#define BUS_SPACE_BARRIER_READ 1
#define BUS_SPACE_BARRIER_WRITE 2
#define M_DEVBUF 0
#ifndef __predict_false
#define __predict_false(v) __builtin_expect(!!(v),0)
#define __predict_true(v) __builtin_expect(!!(v),1)
#endif
#undef KASSERT
#define KASSERT(v) do { if(!(v)) panic("RT3090 assertion %s",#v); } while(0)
#undef DELAY
#define DELAY(us) rtbsd_delay(us)
static inline void rtbsd_delay(unsigned us) { IODelay(us); }
typedef unsigned bus_dma_tag_t;
typedef uint64_t bus_addr_t;
typedef uint32_t bus_size_t;
typedef IOMemoryMap *bus_space_tag_t;
typedef volatile uint8_t *bus_space_handle_t;
struct bus_dma_segment {
    uint64_t ds_addr, ds_len;
    IOBufferMemoryDescriptor *memory;
};
typedef struct bus_dma_segment bus_dma_segment_t;
struct bus_dmamap {
    IODMACommand *command;
    IOBufferMemoryDescriptor *memory;
    void *cpu_buffer;
    mbuf_t packet;
    uint64_t dma_address;
    bool loaded;
    uint64_t dm_mapsize;
    int dm_nsegs;
    unsigned max_segments, max_size, max_segment_size;
    bus_dma_segment_t dm_segs[15];
};
typedef struct bus_dmamap *bus_dmamap_t;
struct device { IOService *provider; void *_data; char dv_xname[16]; };
enum { BUS_DMASYNC_PREREAD, BUS_DMASYNC_PREWRITE, BUS_DMASYNC_POSTREAD, BUS_DMASYNC_POSTWRITE };
bool rtbsd_dma_failed();
void rtbsd_dma_clear_failure();
int bus_dmamap_create(bus_dma_tag_t,bus_size_t,int,bus_size_t,bus_size_t,int,bus_dmamap_t *);
void bus_dmamap_destroy(bus_dma_tag_t,bus_dmamap_t);
int bus_dmamem_alloc(bus_dma_tag_t,bus_size_t,bus_size_t,bus_size_t,bus_dma_segment_t *,int,int *,int);
int bus_dmamem_map(bus_dma_tag_t,bus_dma_segment_t *,int,size_t,caddr_t *,int);
void bus_dmamem_unmap(bus_dma_tag_t,caddr_t,size_t);
void bus_dmamem_free(bus_dma_tag_t,bus_dma_segment_t *,int);
int bus_dmamap_load(bus_dma_tag_t,bus_dmamap_t,void *,bus_size_t,void *,int);
int bus_dmamap_load_mbuf(bus_dma_tag_t,bus_dmamap_t,mbuf_t,int);
void bus_dmamap_unload(bus_dma_tag_t,bus_dmamap_t);
void bus_dmamap_sync(bus_dma_tag_t,bus_dmamap_t,bus_addr_t,bus_size_t,int);
uint32_t bus_space_read_4(bus_space_tag_t,bus_space_handle_t,bus_size_t);
void bus_space_write_4(bus_space_tag_t,bus_space_handle_t,bus_size_t,uint32_t);
void bus_space_write_region_1(bus_space_tag_t,bus_space_handle_t,bus_size_t,const uint8_t *,size_t);
void bus_space_set_region_4(bus_space_tag_t,bus_space_handle_t,bus_size_t,uint32_t,size_t);
void bus_space_barrier(bus_space_tag_t,bus_space_handle_t,bus_size_t,bus_size_t,int);
void config_mountroot(void *,void (*)(struct device *));
int loadfirmware(const char *,uint8_t **,size_t *);
static inline mbuf_t rtbsd_cluster(size_t n) {
    mbuf_t m=nullptr;
    if(mbuf_getcluster(MBUF_DONTWAIT,MBUF_TYPE_DATA,n,&m)) return nullptr;
    mbuf_setlen(m,n); mbuf_pkthdr_setlen(m,n); return m;
}
#define MCLGETL(old,how,n) rtbsd_cluster(n)
static inline void rtbsd_freem(mbuf_t m) { if(m) mbuf_freem(m); }
#define m_freem rtbsd_freem
#include <dev/ic/rt2860reg.h>
#include <dev/ic/rt2860var.h>
#endif
