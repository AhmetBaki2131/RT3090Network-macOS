# Portlama haritası ve sonraki uygulama aşamaları

> Bu belge önceki Diagnostic aşamasının kaydıdır. Yeni 0.2.0 ağ hedefinin
> güncel kod ve test durumu README.md, NETWORK.md ve network-validation.json içindedir.

| Linux | IOKit/macOS yönü | Bu teslimde durum |
|---|---|---|
| pci_driver / pci_dev | IOService personality / IOPCIDevice | PCI ID eşleşmesi, open/close |
| pci_ioremap_bar / readl / writel | mapDeviceMemoryWithRegister / OSRead/WriteLittleInt32 | BAR0, posted-write flush |
| dma_set_mask(32) / dma_map_* | IODMACommand 32 bit IOVM mapping | Mapping denemesi; canlı ring yok |
| dma_alloc_coherent | IOBufferMemoryDescriptor + IODMACommand | Test buffer; cihazla paylaşılmıyor |
| request_irq / hardirq | IOFilterInterruptEventSource | Tasarım yönü; uygulanmadı |
| tasklet / workqueue | IOWorkLoop + IOCommandGate | Canlı veri yolu için uygulanacak |
| timer / delayed_work | IOTimerEventSource | Scan/timeout için uygulanacak |
| mutex / spinlock | workloop gate / IOLock / IOSimpleLock | Core caller serialization şartı; bring-up lifecycle tek akış |
| udelay / msleep | IODelay / IOSleep | Uygulandı; interrupt context'ten çağrılmaz |
| request_firmware | Lisanslı immutable build-time firmware include | SHA/CRC kontrollü, varsayılan kapalı |
| EEPROM 93cx6 / eFuse | rt_bus üzerinden register algoritması | Uygulandı; program/erase opcode yok |
| skb | mbuf + DMA descriptor ömrü | Sadece header/descriptor codec; canlı aktarım yok |
| ieee80211_alloc/register_hw | Soft-MAC yığını + IONetworkingFamily | Henüz yok; bu bir rename işlemi değil |
| mac80211 scan/associate/security | net80211 ve control API/supplicant entegrasyonu | Henüz yok |
| cfg80211 regdomain / rfkill | Kanal/power sınırları ve gerçek RF kill kontrolü | Henüz yok; TX açılmıyor |

## Seçilen geliştirme yolu

Linux RT3090 register/EEPROM/firmware/DMA algoritmalarını ayrı C HAL'ında
tutmak. Önce cihazda EEPROM ve MCU-ready doğrulanmalı. Sonra tam Linux
`rt2800mmio_init_registers`, RT3090 için BBP/RF init, anten ve RF3020/ilgili
RF tipi kalibrasyonu seçilmeli. Sadece register default tablolarını
kopyalamak kalibrasyonun yerine geçmez.

İlk ağ hedefi public IOEthernetController arayüzü ve `itlwm` örneğinde
taşınmış OpenBSD net80211 katmanı. Bu, Apple özel IO80211 ABI'sini ilk
aşamada zorunlu kılmaz; ancak scan/join komutları için kullanıcı arayüzü
ve ayrı control API gerekir. HeliPort, RT3090 için otomatik uyumlu değildir.
`itlwm` kodunu gerçekten entegre etmeden WPA2 hazır denemez. Alternatif
native AirPort yolu 10.13 IO80211Family ABI ve Apple supplicant ile ayrı
doğrulama gerektirir.

Mevcut hedef IOService'tir; **IOEthernetController veya IO80211Controller
değildir**. Ağ portu tamamlanmadan Ethernet arayüzü veya sahte link-up
durumu oluşturulmaması bilinçli bir karardır.

## Uygulama için kabul kapıları

1. **Kimlik/EEPROM:** cihaz PCI ID, subsystem ID, ASIC revision, RF tipi;
   Linux ve macOS EEPROM dump'ları eşleşmeli. Geçersiz MAC/anten sayısıyla TX yok.
2. **MCU:** lisanslı doğru firmware, CRC/SHA, PBF ready ve mailbox cevapları.
   BBP ready, PCI güç durumu ve firmware sonrası yeniden başlatma ölçülmeli.
3. **RF:** gerçek HP kartının EEPROM güç/frekans/LNA/RSSI tabloları, RF kill,
   izinli kanallar, revizyona özel kalibrasyon. EEPROM'a yazma yapılmamalı.
4. **DMA/IRQ:** RX ve AC0..3/MGMT ringleri IOVM olarak adreslenmeli; descriptor
   ownership ve memory barrier'ları. IRQ source W1C ACK, enabled-bit mask,
   filter→workloop handoff, RX budget ve TX FIFO success status.
   DMA-done tek başına TX başarılı demek değildir.
5. **Pasif scan:** RXWI ve 802.11 management paketleriyle gerçek BSS sonuçları,
   kanal dolaşımı/dwell zamanlayıcıları, ülke/regülasyon. SSID parser başarıları
   bu kapıyı geçirmez; gerçek beacon alımı gerekir.
6. **Açık ağ:** authentication/association state machine, RX decapsulation ve
   TX encapsulation, management retry/timeouts; gerçek DHCP/ARP/veri transferi.
7. **WPA2-PSK/CCMP:** PMK/PTK/GTK, dört aşamalı EAPOL, replay/MIC kontrolü,
   key install ve CCMP packet number yönetimi. Yanlış parola, replay ve
   rekey negatif testleri. Sadece RSN IE tespiti WPA2 desteği değildir.
8. **Dayanıklılık:** remove/stop sırasında interrupt kapatma, DMA idle,
   bus-master kapatma ve ardından DMA unmap; suspend/resume; kernel panic
   olmadan tekrar bağlantı ve yükleme/kaldırma.

Core donanım metotlarının dışarıdan serializasyonu şarttır. Şu anda sadece
başlatma/kapatma akışı çalışır; sonraki user client, timer veya IRQ
eklemelerinde IOCommandGate olmadan bu metotlar paylaşılmamalı.
