# İncelenen kaynaklar ve teknik uygulanabilirlik

> Bu belge önceki Diagnostic aşamasının kaydıdır. Yeni 0.2.0 ağ hedefinin
> güncel kod ve test durumu README.md, NETWORK.md ve network-validation.json içindedir.

Kaynak commit'leri `sources.json` içindedir. Araştırma 12 Ekim 2026 tarihinde
bu Linux çalışma alanında yapıldı. Ana depolar gerçekten Git ile indirildi;
aşağıdaki dosya ve fonksiyonlar incelendi.

## Linux donanım yolu

`torvalds/linux`, `drivers/net/wireless/ralink/rt2x00/`:

- `rt2800pci.c`: `PCI_DEVICE(0x1814, 0x3090)` kayıtlıdır.
  Bu, Linux sürücüsünün desteklediği kimliği doğrular; kullanıcının fiziksel
  kartının PCI kimliği henüz ölçülmedi.
- `rt2x00pci.c:rt2x00pci_probe`: BAR0 haritalama, bus mastering, 32 bit DMA
  maskesi, ieee80211 hardware ayırma ve rt2x00 başlatma.
- `rt2800pci.c`: serial EEPROM pinleri ve width seçimi; `rt2860.bin` seçimi;
  `PBF_SYS_CTRL` ile firmware program RAM erişimi.
- `rt2800lib.c`: firmware CRC ve 8 KiB PCI uzunluğu; firmware-ready polling,
  `rt2800_probe_rt`, `rt2800_init_eeprom`, eFuse ters DATA register sırası,
  BBP/RF busy polling ve MCU mailbox. Tam `rt2800_init_rfcsr` ve
  `rt2800_config_channel`/kalibrasyon yolları hâlâ portlanacak.
- `rt2800mmio.c/h`: 16 bayt PCI DMA descriptor'ları, TXWI/payload iki segment,
  RXWI, IRQ ACK ve tasklet bölünmesi; DMA-done ile TX başarı statüsünün farklı olması.
- `rt2x00dev.c`, `rt2x00mac.c`: mac80211 hardware kayıt/başlatma ve protokol
  callback bağımlılıkları. Linux sürücüsü bağımsız bir WPA2 protokol yığını değildir.
- `drivers/misc/eeprom/eeprom_93cx6.c`: READ opcode, clock timing ve MSB-first
  word erişimi. `lib/crc/crc-ccitt.c`: reflected CCITT algoritması.

İncelenen rt2x00 dizininin değişmemiş snapshot'ı `vendor/linux/rt2x00` içinde.
Xcode bu Linux dosyalarını doğrudan derlemez. Portlanan seçili algoritmalar
`src/rt3090_core.c` içindedir; tüm Linux sürücüsü portlandı iddiası yoktur.

## Register ve bellek haritası

| İşlev | Offset / biçim |
|---|---|
| EEPROM serial kontrol | `0x0004`; CLK bit 0, CS bit 1, DI bit 2, DO bit 3 |
| Interrupt source / enable mask | `0x0200` / `0x0204`; source W1C, mask bit 1 = açık |
| DMA global kontrol | `0x0208`; TX enable/busy bit 0/1, RX enable/busy bit 2/3 |
| PBF firmware kontrol / host command | `0x0400` / `0x0404` |
| RF serial CSR | `0x0500` |
| eFuse kontrol / DATA0..3 | `0x0580` / `0x0590..0x059c`; okuma DATA3'ten başlar |
| ASIC revision / BBP CSR | `0x1000` / `0x101c` |
| PCI power pin / autowakeup | `0x1204` / `0x1208` |
| Firmware program RAM | `0x2000..0x3fff`, tam 8192 bayt |
| MCU mailbox / CID / status / BBP agent | `0x7010` / `0x7014` / `0x701c` / `0x7028` |
| EEPROM | 512 bayt; MAC byte 4..9; NIC_CONF0 byte `0x34`; NIC_CONF1 `0x36` |
| TX/RX DMA descriptor | 4 little-endian 32 bit word; pointer alanları 32 bit |
| RT3090 TXWI/RXWI | 16 bayt; DMA descriptor ile aynı şey değildir |

RF tipi yalnızca PCI ID'den çıkarılmaz: NIC_CONF0 RF_TYPE alanı okunmalı.
RT3090 ve RT3070 revizyon farklılıkları/anten çeşitliliği/power tabloları
korunmalıdır. Bu port beklenmeyen ASIC'e firmware yazmayı reddeder ve bozuk
EEPROM için rastgele MAC oluşturmaz; bazı kart varyantlarını bu yüzden reddedebilir.

## macOS örnekleri

- **OpenIntelWireless/itlwm**: `itlwm.cpp/hpp` IOEthernetController arayüzü;
  `ItlIwm.cpp` IOKit → donanım HAL bağlantısı; OpenBSD `net80211` input/proto/crypto
  yolları; `AirportItlwm.cpp` Apple supplicant/PTK bağlantısı incelendi.
  Xcode'da `AirportItlwm-High Sierra` hedefi, deployment 10.13 ve
  `__IO80211_TARGET=__MAC_10_13` mevcut. Bunlar Intel sürücüleridir; PCI ID
  eklemek RT3090'u çalıştırmaz. RT3090 backend yok.
- **acidanthera/MacKernelSDK**: belgeleri, IOPCIDevice/IODMACommand/IOBufferMemoryDescriptor
  ve IO80211Controller başlıkları incelendi. macOS 11 SDK tabanlıdır; eski
  kernel için compatibility guard ve libkmod sunar. **Apple 10.13 SDK'sı değildir.**
  IO80211Controller özel/reverse-engineered başlıkları ABI garantisi sayılmaz.
- **Apple-OSS-Distributions/IONetworkingFamily**: public Ethernet API kaynağı
  ve ayrıca `IONetworkingFamily-139.60.1` tag'inin IOEthernetController.h
  donanım adresi API'si incelendi. Public Ethernet API, Wi-Fi state machine sağlamaz.
- **mercurysquad/VoodooWireless**: framework ve eski IO80211 başlıkları,
  cipher kaynakları incelendi; RT3090 donanım backend'i bulunmadı. İncelenen
  somut cipher implementasyonu WEP; WPA2 enum isimleri çalışan WPA2 kanıtı değildir.
- **chris1111/Wireless-Ralink-Panel-Utility**: README Snow Leopard–Catalina
  aralığı iddia ediyor ama kurduğu kext `RT2870USBWirelessDriver.kext`.
  Destek listesi USB ürünler; RT3090 PCIe çözümü değil. Release binary'si
  indirilmedi, binary uyumluluğu test edilmedi. Bu paketin SIP/system-file
  talimatları bu projeye taşınmadı.

**Sonuç:** İncelenen erişilebilir projelerde doğrulanmış High Sierra RT3090
PCIe sürücüsü bulunamadı. Bu, böyle bir sürücünün hiçbir yerde olmadığı
anlamına gelmez. GitHub repository-search API istekleri proxy tarafından
403 ile reddedildi; genel web arama aracı yok. Eski OEM Ralink PCI binary
paketleri ve forum arşivleri kapsamlı doğrulanamadı. Bilinmeyen binary'yi
kernel'e yüklemek veya USB plist'ine PCI ID eklemek önerilmiyor.

## Firmware provenance

İncelenen dosya `wkennington/linux-firmware` GitHub mirror'ındaki
`rt2860.bin`; commit `sources.json` içinde. Bu üçüncü taraf mirror, güncel
resmî linux-firmware deposu olarak sunulmuyor.

SHA-256:
`67d5e8b32293cc2f31f67ebb112d4dabf1e23019a11c517036ba42cb48e4159c`

8192 bayt ve Linux'la aynı CRC algoritması test edildi. CRC, kriptografik
imza veya donanım uyumluluk kanıtı değildir; build helper ayrıca bu SHA-256'yı
denetler. Firmware binary'si dağıtılan ZIP'te veya varsayılan kext derlemesinde
yok. Lisans ayrı ve değişmeden saklandı; özellikle patent lisansının OSI
lisanslı işletim sistemiyle kombinasyon koşulu macOS kullanım/dağıtımı için
ayrıca değerlendirilmelidir. Linux GPL lisansı firmware'e uygulanamaz.

## Neden tamamlanmış Wi-Fi sürücüsü teslim edilemiyor?

Mac/Xcode ve gerçek kart erişimi yok. Bunların yanında portun kendisinde
tam RF init/kalibrasyon, canlı DMA/IRQ, scan/association ve WPA2 veri yolları
eksik. Mac bulunması bu eksikleri otomatik tamamlamaz. RT3090 bir soft-MAC
aygıtıdır; firmware yüklemek bütün Wi-Fi protokolünü sağlamaz. Public IOKit
metotları Linux mac80211 callback'lerine bire bir eşdeğer değildir.

Bu oturumda donanımdan bağımsız derlenip sınanabilen kod ve IOKit bring-up
bağlantısı geliştirildi. Tam sürücü, sonraki kod geliştirme ve cihaz üzerinde
kontrollü doğrulama gerektirir.
