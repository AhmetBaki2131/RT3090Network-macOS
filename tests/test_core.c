/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "rt3090_core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { checks++; if(!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); exit(1); } } while(0)
static unsigned checks;
struct model {
    uint32_t regs[0x8000/4];
    uint8_t eeprom[512];
    unsigned writes, fw_writes, delays, pbf_stuck, efuse_stuck, dma_stuck;
    unsigned ee_width, ee_bits, ee_command, ee_read_bit, ee_address;
    uint32_t ee_last;
    int ee_reading, ee_bad_opcode;
};
static uint32_t rd(void *ctx,uint32_t reg)
{
    struct model *m=ctx;
    if(reg>=0x8000 || reg%4) return 0xffffffff;
    if(reg==RT_E2PROM_CSR && m->ee_reading) {
        unsigned a=m->ee_address;
        uint16_t word=(uint16_t)(m->eeprom[a*2]|((uint16_t)m->eeprom[a*2+1]<<8));
        return m->ee_last|((uint32_t)((word>>(15-m->ee_read_bit))&1)<<3);
    }
    return m->regs[reg/4];
}
static void wr(void *ctx,uint32_t reg,uint32_t value)
{
    struct model *m=ctx;
    if(reg>=0x8000||reg%4) abort();
    m->writes++;
    if(reg>=RT_FIRMWARE_BASE && reg<RT_FIRMWARE_BASE+RT_FIRMWARE_SIZE) m->fw_writes++;
    if(reg==RT_E2PROM_CSR) {
        uint32_t old=m->ee_last;
        if(!(old&2) && (value&2)) {
            m->ee_bits=0; m->ee_command=0; m->ee_reading=0; m->ee_read_bit=0;
        }
        if((value&2) && (old&1) && !(value&1)) {
            if(m->ee_reading) {
                if(m->ee_read_bit<15) m->ee_read_bit++;
            } else if(m->ee_bits==0) m->ee_bits++; /* startup pulse */
            else {
                m->ee_command=(m->ee_command<<1)|((value>>2)&1);
                m->ee_bits++;
                if(m->ee_bits==m->ee_width+4) {
                    if((m->ee_command>>m->ee_width)!=6) m->ee_bad_opcode=1;
                    m->ee_address=m->ee_command&((1u<<m->ee_width)-1);
                    m->ee_reading=1;
                }
            }
        }
        if(!(value&2)) m->ee_reading=0;
        m->ee_last=value;
    }
    if(reg==RT_EFUSE_CTRL && (value&0x40000000) && !m->efuse_stuck) {
        unsigned word=(value&0x03fe0000)>>17,j;
        static const uint32_t data_regs[]={RT_EFUSE_DATA3,RT_EFUSE_DATA2,RT_EFUSE_DATA1,RT_EFUSE_DATA0};
        for(j=0;j<4;j++) {
            unsigned a=word*2+j*4;
            m->regs[data_regs[j]/4]=(uint32_t)m->eeprom[a]|((uint32_t)m->eeprom[a+1]<<8)|((uint32_t)m->eeprom[a+2]<<16)|((uint32_t)m->eeprom[a+3]<<24);
        }
        value&=~0x40000000u;
    }
    if(reg==RT_WPDMA && m->dma_stuck) value|=0xa;
    if(reg==RT_PBF_SYS_CTRL && value==1 && !m->pbf_stuck) value|=0x80;
    if(reg==RT_RF_CSR || reg==RT_BBP_CSR) value=(value&~0x20000u)|0x5a;
    m->regs[reg/4]=value;
}
static void delay(void *ctx,uint32_t us) { struct model *m=ctx; m->delays+=us; }
static struct rt_bus bus(struct model *m) { struct rt_bus b={m,rd,wr,delay}; return b; }
static void valid_eeprom(uint8_t *e)
{
    unsigned i; for(i=0;i<512;i++) e[i]=(uint8_t)i;
    e[4]=0x02; e[5]=0x11; e[6]=0x22; e[7]=0x33; e[8]=0x44; e[9]=0x55;
    e[0x34]=0x11; e[0x35]=5;
}
static void valid_firmware(uint8_t *p)
{
    uint16_t crc; unsigned i;
    for(i=0;i<8190;i++) p[i]=(uint8_t)(i*7);
    crc=rt_crc_ccitt(p,8190);
    p[8190]=(uint8_t)crc; p[8191]=(uint8_t)(crc>>8);
}
static void test_firmware(const char *real_path)
{
    uint8_t fw[8192]; struct model m={0}; struct rt_bus b=bus(&m); unsigned before;
    CHECK(rt_crc_ccitt((const uint8_t *)"123456789",9)==0x6f91);
    valid_firmware(fw); CHECK(rt_check_firmware(fw,sizeof fw)==RT_OK);
    fw[0]^=1; CHECK(rt_check_firmware(fw,sizeof fw)==RT_BAD_CRC);
    CHECK(rt_boot_firmware(&b,fw,sizeof fw)==RT_BAD_CRC); CHECK(m.writes==0);
    fw[0]^=1; CHECK(rt_check_firmware(fw,8191)==RT_INVALID);
    CHECK(rt_check_firmware(NULL,8192)==RT_INVALID);
    m.regs[RT_MAC_CSR0/4]=0x30900211;
    CHECK(rt_boot_firmware(&b,fw,sizeof fw)==RT_OK);
    CHECK(m.fw_writes==2048); CHECK(m.regs[RT_FIRMWARE_BASE/4]==0x150e0700);
    CHECK((m.regs[RT_WPDMA/4]&5)==0); CHECK(m.regs[RT_INT_MASK/4]==0);
    before=m.writes; m.regs[RT_MAC_CSR0/4]=0x53900211;
    CHECK(rt_boot_firmware(&b,fw,sizeof fw)==RT_UNSUPPORTED); CHECK(m.writes==before);
    m.regs[RT_MAC_CSR0/4]=0x30900211; m.pbf_stuck=1;
    CHECK(rt_boot_firmware(&b,fw,sizeof fw)==RT_TIMEOUT);
    m.dma_stuck=1; CHECK(rt_quiesce(&b)==RT_TIMEOUT);
    m.regs[RT_WPDMA/4]=0xffffffff; CHECK(rt_quiesce(&b)==RT_REMOVED);
    if(real_path) {
        FILE *f=fopen(real_path,"rb"); CHECK(f!=NULL);
        CHECK(fread(fw,1,8192,f)==8192); CHECK(fgetc(f)==EOF); CHECK(fclose(f)==0);
        CHECK(rt_check_firmware(fw,sizeof fw)==RT_OK);
        puts("Actual rt2860.bin length and Linux-compatible CRC: PASS");
    }
}
static void test_eeprom(void)
{
    struct model m={0}; struct rt_bus b=bus(&m); uint8_t out[512]; struct rt_identity id;
    valid_eeprom(m.eeprom); m.regs[RT_EFUSE_CTRL/4]=0x80000000;
    CHECK(rt_read_eeprom(&b,out)==RT_OK); CHECK(memcmp(out,m.eeprom,512)==0);
    CHECK(rt_parse_eeprom(out,512,&id)==RT_OK); CHECK(id.rf_type==5 && id.tx_chains==1 && id.rx_chains==1);
    CHECK(memcmp(id.mac,m.eeprom+4,6)==0); CHECK(rt_parse_eeprom(out,511,&id)==RT_INVALID);
    out[4]|=1; CHECK(rt_parse_eeprom(out,512,&id)==RT_INVALID); out[4]&=~1;
    out[0x34]=0x31; CHECK(rt_parse_eeprom(out,512,&id)==RT_UNSUPPORTED);
    m.efuse_stuck=1; CHECK(rt_read_eeprom(&b,out)==RT_TIMEOUT);
    m.efuse_stuck=0; m.regs[RT_EFUSE_CTRL/4]=0;
    m.regs[RT_E2PROM_CSR/4]=0x10; m.ee_width=8;
    CHECK(rt_read_eeprom(&b,out)==RT_OK); CHECK(memcmp(out,m.eeprom,512)==0); CHECK(!m.ee_bad_opcode);
    CHECK((m.ee_last&6)==0);
    m.regs[RT_E2PROM_CSR/4]=0x20; m.ee_width=10;
    CHECK(rt_read_eeprom(&b,out)==RT_OK); CHECK(memcmp(out,m.eeprom,512)==0);
    m.regs[RT_E2PROM_CSR/4]=0; m.ee_width=6;
    CHECK(rt_read_eeprom(&b,out)==RT_OK); CHECK(memcmp(out,m.eeprom,128)==0);
    CHECK(memcmp(out,out+128,128)==0); /* small EEPROM address wrap */
}
static void test_descriptors(void)
{
    struct rt_descriptor d; struct rt_rx_info rx;
    CHECK(sizeof d==16);
    CHECK(rt_tx_descriptor(&d,0x1000,16,0x2000,100,0,0,0)==RT_OK);
    CHECK(d.bytes[4]==100 && d.bytes[5]==0x40 && d.bytes[6]==16 && d.bytes[7]==0);
    CHECK(d.bytes[15]==5);
    CHECK(rt_tx_descriptor(&d,0x1000,16,0x2000,100,1,1,1)==RT_OK);
    CHECK(d.bytes[5]==0x80 && d.bytes[15]==4);
    CHECK(rt_tx_descriptor(&d,0x100000000ULL,16,0x2000,100,0,0,0)==RT_INVALID);
    CHECK(rt_tx_descriptor(&d,0xfffffff8u,16,0x2000,100,0,0,0)==RT_INVALID);
    CHECK(rt_rx_descriptor(&d,0xfffff000u,4096)==RT_OK);
    CHECK(rt_rx_descriptor(&d,0xfffff001u,4096)==RT_INVALID);
    CHECK(rt_rx_descriptor(&d,0x1000,4096)==RT_OK);
    CHECK(rt_rx_complete(&d,4096,&rx)==RT_BUSY);
    d.bytes[6]=100; d.bytes[7]=0x80; d.bytes[13]=0x43; d.bytes[14]=1;
    CHECK(rt_rx_complete(&d,4096,&rx)==RT_OK);
    CHECK(rx.length==100 && rx.crc_error && rx.cipher_error==1 && rx.decrypted && rx.l2_padding);
    CHECK(rt_rx_complete(&d,99,&rx)==RT_INVALID);
}
static void test_serial(void)
{
    struct model m={0}; struct rt_bus b=bus(&m); uint8_t value; uint32_t chip;
    CHECK(rt_wait_chip(&b,&chip)==RT_TIMEOUT);
    m.regs[RT_MAC_CSR0/4]=0x30900211; CHECK(rt_wait_chip(&b,&chip)==RT_OK);
    CHECK(chip==0x30900211);
    CHECK(rt_bbp_read(&b,0,&value)==RT_OK && value==0x5a);
    CHECK(rt_bbp_write(&b,3,0x10)==RT_OK);
    CHECK(rt_rf_read(&b,31,&value)==RT_OK && value==0x5a);
    CHECK(rt_rf_write(&b,31,0x10)==RT_OK);
    CHECK(rt_rf_read(&b,64,&value)==RT_INVALID);
    m.regs[RT_RF_CSR/4]=0x20000; CHECK(rt_rf_read(&b,0,&value)==RT_TIMEOUT);
    m.regs[RT_BBP_CSR/4]=0xffffffff; CHECK(rt_bbp_read(&b,0,&value)==RT_REMOVED);
    m.regs[RT_H2M_CID/4]=0xffff42ff; m.regs[RT_H2M_STATUS/4]=0x00000100;
    CHECK(rt_mcu_command(&b,0x31,0x42,0,0)==RT_OK);
    CHECK(m.regs[RT_HOST_CMD/4]==0x31);
    CHECK(rt_mcu_command(&b,0x31,255,0,0)==RT_INVALID);
    m.regs[RT_H2M_MAILBOX/4]=0; CHECK(rt_mcu_command(&b,0x31,0x43,0,0)==RT_TIMEOUT);
}
static void test_wireless_info(void)
{
    uint8_t p[128]={0}; struct rt_rxwi_info r;
    CHECK(rt_txwi_legacy(p,100,0,0,255,1,0,1)==RT_OK);
    CHECK(p[0]==0 && p[3]==0 && p[4]==2 && p[5]==255 && p[6]==100 && p[7]==16);
    CHECK(rt_txwi_legacy(p,100,1,7,2,2,1,0)==RT_OK);
    CHECK(p[2]==7 && p[3]==0x40 && p[4]==1);
    CHECK(rt_txwi_legacy(p,100,0,4,0,0,0,0)==RT_INVALID);
    CHECK(rt_txwi_legacy(p,100,1,8,0,0,0,0)==RT_INVALID);
    CHECK(rt_txwi_legacy(p,4096,0,0,0,0,0,0)==RT_INVALID);
    memset(p,0,sizeof p); p[0]=3; p[1]=2; p[2]=36; p[3]=0x50;
    p[4]=0x30; p[5]=0x12; p[6]=7; p[7]=0x41; p[8]=40; p[9]=41; p[12]=15;
    CHECK(rt_parse_rxwi(p,52,&r)==RT_OK);
    CHECK(r.mpdu_length==36 && r.wcid==3 && r.key_index==2 && r.tid==5);
    CHECK(r.sequence==0x123 && r.mcs==7 && r.phy_mode==1 && r.short_gi);
    CHECK(r.rssi[0]==40 && r.rssi[1]==41 && r.snr[0]==15);
    CHECK(rt_parse_rxwi(p,51,&r)==RT_INVALID);
    CHECK(rt_parse_rxwi(p,15,&r)==RT_INVALID);
}
static size_t beacon(uint8_t *p)
{
    static const uint8_t ies[]={0,4,'t','e','s','t',3,1,6,
        48,20,1,0,0,15,172,4,1,0,0,15,172,4,1,0,0,15,172,2,0,0};
    memset(p,0,128); p[0]=0x80; p[16]=2; p[32]=100; p[34]=0x10;
    memcpy(p+36,ies,sizeof ies); return 36+sizeof ies;
}
static void test_beacons(void)
{
    uint8_t p[128]; struct rt_bss b; size_t n=beacon(p),i,j; uint32_t random=1;
    CHECK(rt_parse_beacon(p,n,&b)==RT_OK);
    CHECK(b.channel==6 && b.ssid_len==4 && memcmp(b.ssid,"test",4)==0);
    CHECK(b.rsn && b.ccmp_group && b.ccmp_pairwise && b.psk && b.privacy);
    CHECK(rt_parse_beacon(p,n-1,&b)==RT_INVALID);
    p[0]=0x50; CHECK(rt_parse_beacon(p,n,&b)==RT_OK);
    p[0]=8; CHECK(rt_parse_beacon(p,n,&b)==RT_UNSUPPORTED);
    n=beacon(p); p[37]=33; CHECK(rt_parse_beacon(p,n,&b)==RT_INVALID);
    n=beacon(p); p[44]=0; CHECK(rt_parse_beacon(p,n,&b)==RT_INVALID);
    n=beacon(p); p[53]=255; CHECK(rt_parse_beacon(p,n,&b)==RT_INVALID);
    for(i=0;i<5000;i++) {
        for(j=0;j<sizeof p;j++) { random=random*1664525u+1013904223u; p[j]=(uint8_t)(random>>24); }
        p[0]=0x80; p[1]=0; (void)rt_parse_beacon(p,i%129,&b);
    }
    checks++; puts("5000 bounded malformed-frame inputs: completed");
}
int main(int argc,char **argv)
{
    test_firmware(argc>1?argv[1]:NULL); test_eeprom(); test_descriptors(); test_serial(); test_wireless_info(); test_beacons();
    printf("PASS: %u assertions; simulated hardware only\n",checks); return 0;
}
