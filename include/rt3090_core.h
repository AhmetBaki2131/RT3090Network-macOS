/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef RT3090_CORE_H
#define RT3090_CORE_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Read at most n bytes of a caller-owned valid buffer. Invalid/null/wrapping ranges return NULL. */
void *rt_memchr(const void *, int, size_t);
int rt_ring_distance(uint32_t first, uint32_t end, uint32_t size, uint32_t *distance);
int rt_pci_is_target(uint16_t vendor, uint16_t device, uint16_t subvendor, uint16_t subsystem);
enum rt_status { RT_OK=0, RT_INVALID=-1, RT_TIMEOUT=-2, RT_REMOVED=-3,
    RT_BAD_CRC=-4, RT_UNSUPPORTED=-5, RT_BUSY=-6 };
enum {
    RT_EEPROM_SIZE=512, RT_FIRMWARE_SIZE=8192,
    RT_E2PROM_CSR=0x0004, RT_INT_SOURCE=0x0200, RT_INT_MASK=0x0204,
    RT_WPDMA=0x0208, RT_PBF_SYS_CTRL=0x0400, RT_HOST_CMD=0x0404,
    RT_RF_CSR=0x0500, RT_EFUSE_CTRL=0x0580,
    RT_EFUSE_DATA0=0x0590, RT_EFUSE_DATA1=0x0594,
    RT_EFUSE_DATA2=0x0598, RT_EFUSE_DATA3=0x059c,
    RT_MAC_CSR0=0x1000, RT_BBP_CSR=0x101c, RT_AUTOWAKEUP=0x1208,
    RT_PWR_PIN_CFG=0x1204, RT_FIRMWARE_BASE=0x2000,
    RT_H2M_MAILBOX=0x7010, RT_H2M_CID=0x7014,
    RT_H2M_STATUS=0x701c, RT_H2M_BBP_AGENT=0x7028
};
/* Callbacks must use device-ordered LE MMIO with posted-write flushing.
 * Caller must serialize all hardware operations; none is IRQ-safe. */
struct rt_bus {
    void *context;
    uint32_t (*read32)(void *, uint32_t);
    void (*write32)(void *, uint32_t, uint32_t);
    void (*delay_us)(void *, uint32_t);
};
struct rt_identity {
    uint8_t mac[6];
    uint8_t rf_type, tx_chains, rx_chains;
    uint16_t version, nic_conf1, frequency;
};
struct rt_descriptor { uint8_t bytes[16]; };
struct rt_rx_info {
    uint16_t length;
    uint8_t cipher_error, crc_error, decrypted, l2_padding;
};
uint16_t rt_crc_ccitt(const uint8_t *, size_t);
int rt_check_firmware(const uint8_t *, size_t);
int rt_wait_chip(const struct rt_bus *, uint32_t *);
int rt_read_eeprom(const struct rt_bus *, uint8_t out[RT_EEPROM_SIZE]);
int rt_parse_eeprom(const uint8_t *, size_t, struct rt_identity *);
/* Firmware-only bring-up, not radio initialization. DMA remains disabled. */
int rt_boot_firmware(const struct rt_bus *, const uint8_t *, size_t);
int rt_quiesce(const struct rt_bus *);
int rt_mcu_command(const struct rt_bus *, uint8_t, uint8_t, uint8_t, uint8_t);
int rt_bbp_read(const struct rt_bus *, uint8_t, uint8_t *);
int rt_bbp_write(const struct rt_bus *, uint8_t, uint8_t);
int rt_rf_read(const struct rt_bus *, uint8_t, uint8_t *);
int rt_rf_write(const struct rt_bus *, uint8_t, uint8_t);
/* Encodes descriptors only: no allocation, ownership transfer or MMIO kick.
 * TXWI address and payload address must be separate DMA-visible segments. */
int rt_tx_descriptor(struct rt_descriptor *, uint64_t txwi, uint16_t txwi_len,
    uint64_t payload, uint16_t payload_len, int more_frag, int burst, int hw_iv);
int rt_rx_descriptor(struct rt_descriptor *, uint64_t buffer, uint16_t capacity);
int rt_rx_complete(const struct rt_descriptor *, uint16_t capacity, struct rt_rx_info *);
/* RT3090 4-word wireless information headers. No rate-control policy. */
int rt_txwi_legacy(uint8_t out[16], uint16_t mpdu_length, uint8_t phy_mode,
    uint8_t mcs, uint8_t wcid, uint8_t packet_id, int ack, int preserve_sequence);
struct rt_rxwi_info {
    uint16_t mpdu_length, sequence;
    uint8_t wcid, key_index, tid, mcs, phy_mode, bandwidth40, short_gi;
    uint8_t rssi[3], snr[2];
};
int rt_parse_rxwi(const uint8_t *, size_t, struct rt_rxwi_info *);
/* Passive beacon/probe-response decoder, not a scan engine or WPA supplicant. */
struct rt_bss {
    uint8_t bssid[6], ssid[32], ssid_len, channel, privacy;
    uint8_t rsn, ccmp_group, ccmp_pairwise, psk;
    uint16_t beacon_interval;
};
int rt_parse_beacon(const uint8_t *, size_t, struct rt_bss *);
#ifdef __cplusplus
}
#endif
#endif
