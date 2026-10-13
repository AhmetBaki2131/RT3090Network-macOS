# RT3090Network — Ralink RT3090 macOS portu

**Durum: 0.3.4 deneysel sürüm.** [Kext ve kontrol uygulamasını indir](releases/0.3.4/RT3090Network-test.zip) · [Kaynak ZIP](releases/0.3.4/RT3090Network-source.zip) · [Test ve geri alma](releases/0.3.4/NETWORK-TEST.md).

Bu depo, HP Pavilion dv6 kartı için macOS High Sierra portunun kaynak ağacıdır. GitHub depo adı eski `Offline-Games` adıdır; GitHub API erişimi olmadığı için uzaktan yeniden adlandırılmadı.

# RT3090Network 0.3.4

HP Pavilion dv6 üzerindeki Ralink RT3090 (1814:3090 / 103c:1453), macOS High Sierra 10.13.6 x86_64 için deneysel ağ sürücüsü. Mevcut portun devamıdır; normal paket gerçek firmware/radyo/DMA/802.11/WPA2 kodunu içerir. Donanımda kullanılabilir internet bağlantısı doğrulanmadı. Kullanıcı önceki sürümlerde gerçek ağ taraması, Connect sonrasında tam donma ve daha sonra yüklü kext'e rağmen boş IORegistry bildirdi.

Güncel değişiklikler: [AUDIT-0.3.4.md](docs/AUDIT-0.3.4.md). WPA2:0, EAPOL ve durum aktarımı: [WPA2-0.3.4.md](docs/WPA2-0.3.4.md). Geçici doğrulama/yükleme: [NETWORK.md](docs/NETWORK.md). Yapılan cloud kontrollerinin kayıtları ZIP'in verification klasöründedir. Host testleri gerçek PCI, DMA, IRQ, High Sierra ABI veya modem testlerinin yerine geçmez.

## Paket

- RT3090Network.kext: normal ağ modu; imzasız, fiziksel doğrulama gerekir.
- diagnostic/RT3090Network.kext: PCI-only alternatif; aynı bundle identifier nedeniyle normal kext ile birlikte yüklenmez.
- RT3090 Control.app ve rt3090ctl.py: sistem Python 2.7/Tk ile Scan, Connect, Disconnect, Status, DHCP, Check. App kext kurmaz/yüklemez.
- rt3090-test.command: yalnızca açıkça istenen geçici test işlemleri. Varsayılan check yükleme yapmaz; load önce doğrular ve mevcut yüklü modül varsa durur.
- Kaynak ZIP: Xcode projesi, yerel BSD/HAL fork'ları, vendor kaynakları/lisanslar, firmware, testler ve build scriptleri.

EFI/OpenCore/ACPI/SMBIOS/SIP değiştirilmez. Kalıcı veya otomatik kext kurulumu yapılmaz. Önceden Easy Kext Pro/EFI ile kurulmuş kopyalar bu paket tarafından kaldırılmaz.

## Derleme

Native hedef: Xcode 9.4.1, MacOSX10.13.sdk, x86_64. Kaynak araçlarını çalıştırmak için Python 3 gerekir; son kullanıcı kontrol aracı Python 2.7 ile uyumludur. MacKernelSDK header snapshot'ı tam High Sierra SDK değildir.

```bash
sh scripts/build-network-macos.sh
```

Varsayılan derleme paket içindeki pinned firmware'i doğrular ve içerir; eksik/bozuk firmware ile sessizce radio'suz network kext üretmez. PCI-only alternatif:

```bash
RT3090_NETWORK_ENABLED=0 sh scripts/build-network-macos.sh
```

Cloud'da Clang/ld64 ile gerçek Mach-O bundle bağlanır. Native Xcode/kextutil ve hardware scan/handshake/internet bu ortamda çalıştırılmadı. Eski fiziksel sonuçlar yeni sürüm doğrulaması değildir.

## Kaynak/lisans

Linux rt2x00/rt2800 kaynak analizi, OpenBSD RT2860/RT3090 HAL ve itlwm net80211 uyarlaması temel alınır. Değiştirilen BSD bileşenleri port/ içinde ayrı fork'lardır; vendor asılları korunur. [THIRD_PARTY.md](THIRD_PARTY.md), licenses/ ve sources.json kaynak/provenance bilgilerini içerir. rt2860.bin ayrı Ralink firmware lisansını korur. Geçmiş aşama raporlarının içindeki sürüm/komutlar güncel paket talimatı değildir.

## Son gerçek cihaz gözlemi

Ekim 2026 testi: `MCU completion timeout cmd=48` (SLEEP) sonrası radyo başlatması durdu. Ağ taraması önceki sürümde kullanıcı tarafından gözlendi; 0.3.4 için WPA2/DHCP başarısı doğrulanmadı. [MCU karşılaştırması](docs/MCU-COMPARISON.md).
