/* SPDX-License-Identifier: GPL-2.0-or-later
 * Hardware operations adapted from Linux rt2800pci.c, rt2800lib.c,
 * rt2800mmio.c and eeprom_93cx6.c. Original copyrights and source
 * snapshots are retained in vendor/linux and THIRD_PARTY.md.
 * This is a partial port; it contains no mac80211 replacement.
 */
#include "rt3090_core.h"
static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0]|((uint16_t)p[1]<<8)); }
static uint32_t le32(const uint8_t *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
static void put32(uint8_t *p, uint32_t v) { unsigned i; for(i=0;i<4;i++) p[i]=(uint8_t)(v>>(8*i)); }
static int bus_ok(const struct rt_bus *b) { return b && b->read32 && b->write32 && b->delay_us; }
static int wait_mask(const struct rt_bus *b, uint32_t reg, uint32_t mask,
    uint32_t want, unsigned count, unsigned delay, uint32_t *out)
{
    unsigned i; uint32_t v;
    for(i=0;i<count;i++) {
        v=b->read32(b->context,reg);
        if(v==0xffffffffu) return RT_REMOVED;
        if((v&mask)==want) { if(out) *out=v; return RT_OK; }
        b->delay_us(b->context,delay);
    }
    return RT_TIMEOUT;
}
uint16_t rt_crc_ccitt(const uint8_t *p, size_t n)
{
    uint16_t crc=0xffff; size_t i; unsigned bit;
    for(i=0;i<n;i++) {
        crc^=p[i];
        for(bit=0;bit<8;bit++) crc=(uint16_t)((crc>>1)^((crc&1)?0x8408:0));
    }
    return crc;
}
int rt_check_firmware(const uint8_t *p, size_t n)
{
    uint16_t crc, expected;
    /* Exact PCI RT3090 image size. Deliberately reject concatenated images
     * which could overwrite MMIO outside the 8 KiB firmware window. */
    if(!p || n!=RT_FIRMWARE_SIZE) return RT_INVALID;
    expected=(uint16_t)(((uint16_t)p[n-2]<<8)|p[n-1]);
    crc=rt_crc_ccitt(p,n-2);
    crc=(uint16_t)((crc<<8)|(crc>>8));
    return crc==expected ? RT_OK : RT_BAD_CRC;
}
int rt_wait_chip(const struct rt_bus *b, uint32_t *out)
{
    unsigned i; uint32_t v;
    if(!bus_ok(b)||!out) return RT_INVALID;
    for(i=0;i<100;i++) {
        v=b->read32(b->context,RT_MAC_CSR0);
        if(v && v!=0xffffffffu) { *out=v; return RT_OK; }
        b->delay_us(b->context,1000);
    }
    return RT_TIMEOUT;
}
/* Microwire read-only commands. No erase/write-enable opcodes exist here.
 * 1 us per half-cycle meets Linux's >=450 ns timing requirement. */
static void ee_write(const struct rt_bus *b, uint32_t v) { b->write32(b->context,RT_E2PROM_CSR,v); }
static void ee_pulse(const struct rt_bus *b, uint32_t v)
{
    ee_write(b,v|1u); b->delay_us(b->context,1);
    ee_write(b,v&~1u); b->delay_us(b->context,1);
}
static int ee_word(const struct rt_bus *b, unsigned width, unsigned address, uint16_t *out)
{
    unsigned bits=width+3, i; uint32_t command=(6u<<width)|address;
    uint32_t v=2, sample; uint16_t word=0;
    ee_write(b,v); ee_pulse(b,v);
    for(i=bits;i>0;i--) {
        v=2u|(((command>>(i-1))&1u)<<2);
        ee_write(b,v); ee_pulse(b,v);
    }
    v=2; ee_write(b,v);
    for(i=0;i<16;i++) {
        ee_write(b,v|1u); b->delay_us(b->context,1);
        sample=b->read32(b->context,RT_E2PROM_CSR);
        if(sample==0xffffffffu) { ee_write(b,0); return RT_REMOVED; }
        word=(uint16_t)((word<<1)|((sample>>3)&1u));
        ee_write(b,v); b->delay_us(b->context,1);
    }
    ee_write(b,0); ee_pulse(b,0); *out=word;
    return RT_OK;
}
int rt_read_eeprom(const struct rt_bus *b, uint8_t out[RT_EEPROM_SIZE])
{
    uint32_t ctrl, val; uint16_t word; unsigned i,j,width,type; int rc;
    static const uint32_t regs[4]={RT_EFUSE_DATA3,RT_EFUSE_DATA2,RT_EFUSE_DATA1,RT_EFUSE_DATA0};
    if(!bus_ok(b)||!out) return RT_INVALID;
    ctrl=b->read32(b->context,RT_EFUSE_CTRL);
    if(ctrl==0xffffffffu) return RT_REMOVED;
    if(ctrl&0x80000000u) {
        for(i=0;i<256;i+=8) {
            ctrl=b->read32(b->context,RT_EFUSE_CTRL);
            if(ctrl==0xffffffffu) return RT_REMOVED;
            ctrl=(ctrl&~(0x03fe0000u|0xc0u))|((uint32_t)i<<17)|0x40000000u;
            b->write32(b->context,RT_EFUSE_CTRL,ctrl);
            rc=wait_mask(b,RT_EFUSE_CTRL,0x40000000u,0,100,100,0);
            if(rc) return rc;
            for(j=0;j<4;j++) {
                val=b->read32(b->context,regs[j]);
                /* 0xffffffff is valid EEPROM data, not a bus error here. */
                put32(out+i*2+j*4,val);
            }
        }
        return RT_OK;
    }
    ctrl=b->read32(b->context,RT_E2PROM_CSR);
    if(ctrl==0xffffffffu) return RT_REMOVED;
    type=(ctrl>>4)&3; width=type==0?6:(type==1?8:10);
    for(i=0;i<256;i++) {
        /* Linux's multiread uses a u8 word address even on 93C86. */
        rc=ee_word(b,width,i&((1u<<width)-1u),&word);
        if(rc) return rc;
        out[i*2]=(uint8_t)word; out[i*2+1]=(uint8_t)(word>>8);
    }
    return RT_OK;
}
int rt_parse_eeprom(const uint8_t *p, size_t n, struct rt_identity *out)
{
    struct rt_identity id; unsigned i, allzero=1, allff=1; uint16_t nic;
    if(!p||n<RT_EEPROM_SIZE||!out) return RT_INVALID;
    for(i=0;i<6;i++) { id.mac[i]=p[4+i]; if(p[4+i]) allzero=0; if(p[4+i]!=255) allff=0; }
    if(allzero||allff||(id.mac[0]&1)) return RT_INVALID;
    nic=le16(p+0x34); id.rx_chains=nic&15; id.tx_chains=(nic>>4)&15; id.rf_type=(nic>>8)&15;
    if(!id.rx_chains||id.rx_chains>2||!id.tx_chains||id.tx_chains>2) return RT_UNSUPPORTED;
    /* Retain raw RF type; calibration and RF-specific radio init are pending. */
    id.version=le16(p+2); id.nic_conf1=le16(p+0x36); id.frequency=le16(p+0x3a);
    *out=id; return RT_OK;
}
int rt_quiesce(const struct rt_bus *b)
{
    uint32_t v; int rc;
    if(!bus_ok(b)) return RT_INVALID;
    v=b->read32(b->context,RT_WPDMA);
    if(v==0xffffffffu) return RT_REMOVED;
    b->write32(b->context,RT_INT_MASK,0);
    /* Busy bits are read-only. Never pretend to clear them by writing zero. */
    b->write32(b->context,RT_WPDMA,(v&~5u)|0x40u);
    rc=wait_mask(b,RT_WPDMA,0xau,0,100,10000,0);
    return rc;
}
int rt_boot_firmware(const struct rt_bus *b, const uint8_t *p, size_t n)
{
    uint32_t chip; size_t i; int rc;
    if(!bus_ok(b)) return RT_INVALID;
    rc=rt_check_firmware(p,n); if(rc) return rc;
    rc=rt_wait_chip(b,&chip); if(rc) return rc;
    if((chip>>16)!=0x3090) return RT_UNSUPPORTED;
    rc=rt_quiesce(b); if(rc) return rc;
    b->write32(b->context,RT_AUTOWAKEUP,0);
    b->write32(b->context,RT_PWR_PIN_CFG,2);
    b->write32(b->context,RT_PBF_SYS_CTRL,0x10000);
    for(i=0;i<n;i+=4) b->write32(b->context,RT_FIRMWARE_BASE+(uint32_t)i,le32(p+i));
    b->write32(b->context,RT_PBF_SYS_CTRL,0);
    b->write32(b->context,RT_PBF_SYS_CTRL,1);
    b->write32(b->context,RT_H2M_BBP_AGENT,0);
    b->write32(b->context,RT_H2M_MAILBOX,0);
    rc=wait_mask(b,RT_PBF_SYS_CTRL,0x80,0x80,100,1000,0);
    if(rc) return rc;
    rc=rt_quiesce(b); if(rc) return rc;
    b->write32(b->context,RT_H2M_BBP_AGENT,0);
    b->write32(b->context,RT_H2M_MAILBOX,0);
    b->delay_us(b->context,1000);
    return RT_OK;
}
int rt_mcu_command(const struct rt_bus *b, uint8_t cmd, uint8_t token, uint8_t arg0, uint8_t arg1)
{
    uint32_t v; int rc; unsigned i;
    if(!bus_ok(b)||token==255) return RT_INVALID;
    rc=wait_mask(b,RT_H2M_MAILBOX,0xff000000u,0,100,100,&v); if(rc) return rc;
    b->write32(b->context,RT_H2M_MAILBOX,0x01000000u|((uint32_t)token<<16)|((uint32_t)arg1<<8)|arg0);
    b->write32(b->context,RT_HOST_CMD,cmd);
    for(i=0;i<200;i++) {
        unsigned slot;
        v=b->read32(b->context,RT_H2M_CID);
        /* CID 0xffffffff means empty slots, not necessarily device removal. */
        for(slot=0;slot<4;slot++) if(((v>>(slot*8))&255u)==token) {
            uint32_t status=b->read32(b->context,RT_H2M_STATUS);
            unsigned result=(status>>(slot*8))&255u;
            b->write32(b->context,RT_H2M_STATUS,0xffffffffu);
            b->write32(b->context,RT_H2M_CID,0xffffffffu);
            return result==1?RT_OK:RT_INVALID;
        }
        b->delay_us(b->context,100);
    }
    b->write32(b->context,RT_H2M_STATUS,0xffffffffu);
    b->write32(b->context,RT_H2M_CID,0xffffffffu);
    return RT_TIMEOUT;
}
static int serial(const struct rt_bus *b,uint32_t csr,uint8_t reg,uint8_t *value,int write,int bbp)
{
    uint32_t v; int rc;
    if(!bus_ok(b)||!value||(!bbp && reg>63)) return RT_INVALID;
    rc=wait_mask(b,csr,0x20000,0,100,100,0); if(rc) return rc;
    v=0x20000u|((uint32_t)reg<<8);
    if(bbp) v|=0x80000u|(write?0:0x10000u);
    else if(write) v|=0x10000u;
    if(write) v|=*value;
    b->write32(b->context,csr,v);
    rc=wait_mask(b,csr,0x20000,0,100,100,&v); if(rc) return rc;
    if(!write) *value=(uint8_t)v;
    return RT_OK;
}
int rt_bbp_read(const struct rt_bus *b,uint8_t r,uint8_t *v) { return serial(b,RT_BBP_CSR,r,v,0,1); }
int rt_bbp_write(const struct rt_bus *b,uint8_t r,uint8_t v) { return serial(b,RT_BBP_CSR,r,&v,1,1); }
int rt_rf_read(const struct rt_bus *b,uint8_t r,uint8_t *v) { return serial(b,RT_RF_CSR,r,v,0,0); }
int rt_rf_write(const struct rt_bus *b,uint8_t r,uint8_t v) { return serial(b,RT_RF_CSR,r,&v,1,0); }
static int dma_range(uint64_t a, unsigned n) { return n && a<=0xffffffffu && (uint64_t)(n-1)<=0xffffffffu-a; }
int rt_tx_descriptor(struct rt_descriptor *d,uint64_t a,uint16_t al,uint64_t p,uint16_t pl,int more,int burst,int hw_iv)
{
    if(!d||al!=16||pl>0x3fff||!dma_range(a,al)||!dma_range(p,pl)) return RT_INVALID;
    put32(d->bytes,(uint32_t)a);
    put32(d->bytes+4,pl|((uint32_t)al<<16)|(more?0:0x4000u)|(burst?0x8000u:0));
    put32(d->bytes+8,(uint32_t)p);
    put32(d->bytes+12,0x04000000u|(hw_iv?0:0x01000000u));
    return RT_OK;
}
int rt_rx_descriptor(struct rt_descriptor *d,uint64_t a,uint16_t n)
{
    if(!d||n<16||n>0x3fff||!dma_range(a,n)) return RT_INVALID;
    put32(d->bytes,(uint32_t)a); put32(d->bytes+4,(uint32_t)n<<16);
    put32(d->bytes+8,0); put32(d->bytes+12,0); return RT_OK;
}
int rt_rx_complete(const struct rt_descriptor *d,uint16_t capacity,struct rt_rx_info *out)
{
    struct rt_rx_info r; uint32_t w1,w3;
    if(!d||!out) return RT_INVALID;
    w1=le32(d->bytes+4); w3=le32(d->bytes+12);
    if(!(w1&0x80000000u)) return RT_BUSY;
    r.length=(uint16_t)((w1>>16)&0x3fff);
    if(r.length<16||r.length>capacity) return RT_INVALID;
    r.crc_error=(uint8_t)((w3>>8)&1); r.cipher_error=(uint8_t)((w3>>9)&3);
    r.decrypted=(uint8_t)((w3>>16)&1); r.l2_padding=(uint8_t)((w3>>14)&1);
    *out=r; return RT_OK;
}
int rt_txwi_legacy(uint8_t out[16],uint16_t length,uint8_t phy,uint8_t mcs,
    uint8_t wcid,uint8_t packet_id,int ack,int preserve_sequence)
{
    if(!out||length<24||length>4095||phy>1||mcs>(phy?7:3)||packet_id>15) return RT_INVALID;
    /* CCK/OFDM, 20 MHz, no aggregation/STBC/HT. TX_OP=0 (HTTXOP). */
    put32(out,((uint32_t)phy<<30)|((uint32_t)mcs<<16));
    put32(out+4,(ack?1u:0)|(preserve_sequence?2u:0)|((uint32_t)wcid<<8)|
        ((uint32_t)length<<16)|((uint32_t)packet_id<<28));
    put32(out+8,0); put32(out+12,0); return RT_OK;
}
int rt_parse_rxwi(const uint8_t *p,size_t n,struct rt_rxwi_info *out)
{
    struct rt_rxwi_info r; uint32_t w0,w1; unsigned i;
    if(!p||!out||n<16) return RT_INVALID;
    w0=le32(p); w1=le32(p+4);
    r.mpdu_length=(uint16_t)((w0>>16)&0xfff);
    /* n is total received bytes including RXWI. Caller accounts for any
     * L2 padding and validates 802.11 header length before using payload. */
    if(r.mpdu_length<10||r.mpdu_length>n-16) return RT_INVALID;
    r.wcid=(uint8_t)w0; r.key_index=(uint8_t)((w0>>8)&3); r.tid=(uint8_t)(w0>>28);
    r.sequence=(uint16_t)((w1>>4)&0xfff); r.mcs=(uint8_t)((w1>>16)&0x7f);
    r.bandwidth40=(uint8_t)((w1>>23)&1); r.short_gi=(uint8_t)((w1>>24)&1); r.phy_mode=(uint8_t)(w1>>30);
    for(i=0;i<3;i++) r.rssi[i]=p[8+i];
    for(i=0;i<2;i++) r.snr[i]=p[12+i];
    *out=r; return RT_OK;
}
static int suite(const uint8_t *p, uint8_t type) { return p[0]==0 && p[1]==15 && p[2]==172 && p[3]==type; }
static int parse_rsn(const uint8_t *p,size_t n,struct rt_bss *b)
{
    unsigned count,i; size_t off=2;
    if(n<8||le16(p)!=1) return RT_INVALID;
    b->ccmp_group=(uint8_t)suite(p+off,4); off+=4;
    count=le16(p+off); off+=2;
    if(!count||count>(n-off)/4) return RT_INVALID;
    for(i=0;i<count;i++,off+=4) if(suite(p+off,4)) b->ccmp_pairwise=1;
    if(n-off<2) return RT_INVALID;
    count=le16(p+off); off+=2;
    if(!count||count>(n-off)/4) return RT_INVALID;
    for(i=0;i<count;i++,off+=4) if(suite(p+off,2)) b->psk=1;
    /* Optional capabilities, PMKID list and group-management cipher. */
    if(n>off) { if(n-off<2) return RT_INVALID; off+=2; }
    if(n>off) {
        if(n-off<2) return RT_INVALID;
        count=le16(p+off); off+=2;
        if(count>(n-off)/16) return RT_INVALID;
        off+=(size_t)count*16;
    }
    if(n>off) { if(n-off!=4) return RT_INVALID; off+=4; }
    b->rsn=1; return off==n?RT_OK:RT_INVALID;
}
int rt_parse_beacon(const uint8_t *p,size_t n,struct rt_bss *out)
{
    struct rt_bss b={0}; size_t off=36; unsigned i; int ssid=0,ds=0,rsn=0; uint16_t fc;
    if(!p||!out||n<36) return RT_INVALID;
    fc=le16(p);
    if((fc&0x00ff)!=0x0080 && (fc&0x00ff)!=0x0050) return RT_UNSUPPORTED;
    if(fc&0x4000) return RT_UNSUPPORTED;
    for(i=0;i<6;i++) b.bssid[i]=p[16+i];
    b.beacon_interval=le16(p+32); b.privacy=(uint8_t)((le16(p+34)>>4)&1);
    while(off<n) {
        unsigned id,len;
        if(n-off<2) return RT_INVALID;
        id=p[off++]; len=p[off++];
        if(len>n-off) return RT_INVALID;
        if(id==0) {
            if(ssid++||len>32) return RT_INVALID;
            b.ssid_len=(uint8_t)len; for(i=0;i<len;i++) b.ssid[i]=p[off+i];
        } else if(id==3) {
            if(ds++||len!=1||p[off]<1||p[off]>14) return RT_INVALID;
            b.channel=p[off];
        } else if(id==48) {
            if(rsn++||parse_rsn(p+off,len,&b)) return RT_INVALID;
        }
        off+=len;
    }
    if(!ssid) return RT_INVALID;
    *out=b; return RT_OK;
}

void *rt_memchr(const void *buffer, int value, size_t n)
{
    const unsigned char *p = (const unsigned char *)buffer;
    size_t i;
    if (!p || !n || n > UINTPTR_MAX - (uintptr_t)p) return NULL;
    for (i = 0; i < n; ++i)
        if (p[i] == (unsigned char)value) return (void *)(p + i);
    return NULL;
}

int rt_pci_is_target(uint16_t vendor, uint16_t device, uint16_t subvendor, uint16_t subsystem)
{
    return vendor == 0x1814 && device == 0x3090 && subvendor == 0x103c && subsystem == 0x1453;
}

int rt_ring_distance(uint32_t first, uint32_t end, uint32_t size, uint32_t *distance)
{
    if (!distance || !size || first >= size || end >= size) return RT_INVALID;
    *distance = end >= first ? end - first : size - first + end;
    return RT_OK;
}
