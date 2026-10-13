# 0.3.0 teknik geliştirme/test raporu

Normal ağ çalışma modu ana artifact'te etkin; PCI tanı alternatifi ayrı build.
0.2.3'ten devam edildi; önceki kaynak/artifact'ler korunur. Hardware ID tekrar
istenmedi. EFI/OpenCore/ACPI/SMBIOS/SIP/boot argümanı değiştirilmedi.

## Uygulanan normal yol

PCI primary=0x30901814, secondary=0x1453103C; probe/start gerçek config ID kontrolü.
PCI exclusive open, bus mastering off, IRQ mask off ve bounded WPDMA idle;
EEPROM MAC/chain/RF validation; gerçek 8KiB pinned firmware; RT3090 RF/BBP
calibration/channel yolu; TX/RX ring ve workloop IRQ; net80211 station stack;
IOEthernetController interface; real node cache scan; WPA2-Personal/CCMP
EAPOL/key path; controlled-port sonrası Ethernet packet path mevcut.

Firmware/RF algoritmaları Linux core ve OpenBSD RT3090 backend'den türemeye
devam eder. Yeni bir dummy radio/key method veya synthetic scan listesi yok.
Darwin 17.x target ve fixed HP subsystem match korunur. Board EEPROM alanları
şüpheliyse fallback MAC/power uydurulmaz; start başarısız olur.

## Gated DMA sorununun çözümü

Eskiden packet/IRQ sırasında IODMACommand prepare/complete yapılabiliyordu.
0.3.0 per-map fiziksel contiguous low-32-bit staging buffer + prepared command
kullanır. IOVM Segment32 adresi/uzunluğu tam eşleşmeli ve adres sonu <=4GiB
olmalıdır. Map create gate içinde EWOULDBLOCK; map destroy gate içinde kaynakları
bırakıp hata kaydeder. Runtime load/unload sadece borrowed CPU/mbuf pointer ve
length state değiştirir; sync sınırlı CPU copy + I/O fence yapar. Packets normal
workloop/gate içinde kaldığından ptr lifetime backend ownership'iyle korunur.

RX iki map'ini başlangıçta hazırlar ve swap yapar; old mbuf POSTREAD sonrası
net80211'e gider. TX payload her zaman tek staging segmentidir; ring sync
sadece aktif descriptor'u kopyalar, hardware-owned diğer slot'ları ezmez.
Ring pool/resets device DMA idle olduktan sonra yapılır. BSD timer/node detach
gate içinde, map completion/destruction gate dışında olur. Timeout'ta DMA
memory quarantine korunur; unsafe force free yapılmaz.

Staging copy ek CPU/RAM maliyeti getirir. x86 PCIe coherency, gerçek IOMapper,
DMA performance/ownership ve lifecycle hardware'de ayrıca test edilmelidir.
Host shim gerçek mapping'i taklit etmez; gerçek mapping/prepare/segment-export
çağrıları source'ta MacKernelSDK/IOKit üzerinden kalır. Low-memory constraint
sağlanamazsa init reddedilir; adres kırpılarak çalışıyormuş gibi gösterilmez.

## Scan/WPA2 kontrol ve gözlenebilirlik

SSID raw bytes, BSSID, channel, EEPROM/LNA dönüşümüyle tahmini RSSI dBm ve
privacy/RSN proto/cipher'tan security label gerçek net80211 node'larından gelir.
1T/1R RT3090 için RSSI chain0 kalibrasyonu kullanılır; dBm ölçümü test edilmedi.
Supported operation 2.4GHz b/g channel1–11, WPA2-Personal/CCMP'dir.
RSN supplicant state/port authorization/retries IORegistry'de yayımlanır;
GUI/CLI connection requested ile authorized link'i ayırır. Four-way handshake
runtime doğrulaması veya packet capture cloud'da yapılmadı.

DHCP macOS ipconfig, DNS system resolver, IP ping ve source-IP-bound TLS/HTTPS
check uygulanır. Route test edilen IP/HTTPS host için RT3090 interface olmalı;
başka interface'e route olduğunda başarı verilmez. DNS resolver path separately
scutil --dns ile kontrol edilir. TLS certificate verification açık kalır.
GUI script app sistem Python/Tk/osascript kullanır; root admin prompt kontrol
komutları içindir, kext kurmaz. GUI/Tk/native CLI burada çalıştırılmadı.

## Çalıştırılan doğrulamalar

- Normal + diagnostic build: 48 C/C++ unit + core/kmod, 0 compiler errors.
- ld64-409.12 cross-link: iki ayrı x86_64 MH_KEXT_BUNDLE; version 0.3.0.
- Kmod ctor/dtor, primary/secondary matching, unsupported import checks geçti.
- 493 imports: 354 public XNU export eşleşmesi, 139 family imports; unknown=0.
  Family exports ve target ABI native kextutil ile doğrulanmalıdır.
- Real RTBSDGlue.cpp host-shim testi: initial prepare, gate içinde load/unload
  boyunca prepare/complete counter'larının değişmemesi; scatter mbuf copy;
  POSTREAD copy; invalid length rejection; gated create rejection; 4GiB overflow.
  ASan/UBSan geçti. Bu physical DMA veya IOMMU testi değildir.
- Core 92 assertions + 5000 malformed-frame input; PCI 7 case; ring 20480
  valid pair + invalid inputs; crypto 220 vector ASan/UBSan geçti.
- Diagnostic preprocessed start donanım çağrılarını içermez; network negative
  control bu çağrıları bulur. Bu native runtime safety kanıtı değildir.
- Python GUI/CLI syntax ve app plist/source/executable paths kontrol edildi.
- MacOSX10.13.sdk/Xcode9.4.1 native build, yeni kextutil/load, hardware PCI,
  radio/scan/WPA2/DHCP/Internet/GUI çalıştırılması: YAPILMADI.

## Açık kalan işler / fiziksel gereksinimler

Native High Sierra exported-symbol/vtable ABI validation; real HP EEPROM/MCU
RF calibration and RF-kill; bus mastering/ring/coherency/IRQ delivery; scan AP
results; authentication/association/EAPOL message1–4 and key install; traffic,
DHCP/DNS/TLS tests yapılmalı. Bu kontroller olmadan sürücünün kullanılabilir
Wi-Fi sağladığı söylenmez. Antenna/radio switch veya BIOS PCI power state
Windows data'sından kesin doğrulanamaz; Mac logs'i gerekir.

Sleep/wake/power-management tamamlanmadı. HT/n, enterprise/WPA3, country-specific
channel12/13, native AirPort/IO80211 UI hedefi teslim edilmedi. GUI wrapper için
Tk bulunması ve platform signing/launch policy uygunluğu gereklidir. Testte
native error veya gated destruction log'u varsa sıradaki aşamaya geçilmemeli.

Güvenli native -n -t, manuel staging ve rollback NETWORK.md'dedir. Eski kernel
panic kullanıcı tarafından yanlış EFI hazırlığına bağlandı; bu sürümün de
panic oluşturmayacağı gibi donanımda test edilmemiş bir garanti verilmez.
