> Tarihsel aşama raporu. Güncel sürüm/komutlar README.md, NETWORK.md ve AUDIT-0.3.4.md içindedir; aşağıdaki eski yükleme komutlarını güncel pakete uygulamayın.

# RT3090Network 0.3.3 — association → RUN donması

## Gözlenen fiziksel durum

Kullanıcı 0.3.2 yüklü olduğunu ve en2 arayüzünün oluştuğunu bildirdi. Connect sonrasında kernel logunda 1→0, 0→1, 1→2, 2→3, 3→4 mesajları görüldü ve bilgisayar tamamen dondu. 3→4 mesajı HAL işlemlerinden önce yazılır. Bu gözlem RUN'ın tamamlandığını, WPA2'nin yetkilendirildiğini veya internete erişildiğini kanıtlamaz. Panic/backtrace sağlanmadı; kök neden kesinleştirilmedi.

## Yapılan düzeltmeler

- `rt2860_newstate`: RUN'ın timer, kanal, slot, fallback/basic rates, preamble, BSSID, newassoc, TSF ve LED alt adımları tek tek izlenir. Sticky I/O/DMA hatası görüldüğünde sonraki alt adımlara ve net80211 state callback'ine geçilmez. Interrupt maskesi kapatılır; kontrolcü IRQ/tick yolu sürücüyü durdurur.
- NULL BSS/kanal, mevcut DMA/I/O hatası, NULL/recursive state callback reddedilir. Callback'in kendisini tekrar çağırması sınırsız rekürsiyon oluşturamaz.
- 0.3.2'de `newassoc` geçersiz rate set için io_failed bildiriyordu, fakat çağıran RUN yolu yine net80211'e ilerleyebiliyordu. Alt katmandaki boş/geçersiz rate panic'i böylece hâlâ erişilebilirdi. Bu yol artık reddedilir. Bu durumun kullanıcının modeminde gerçekleştiği kanıtlanmadı.
- Yerel `ieee80211_proto.c` fork'u geçersiz RUN rate/TX-rate/BSS durumunu state değişiminden önce EINVAL ile reddeder; bu durumda host panic çağırmaz.
- MCU mailbox busy/completion timeout ve başarısız MCU status artık sticky io_failed işaretler. Daha önce dönüş değeri bazı void HAL çağrılarında kaybolabiliyordu. Beklemeler zaten sınırlıydı; mevcut süre sınırları korunur.
- Hardware key table erişiminden önce cipher key uzunluğu, key ID 0..3, pairwise node ve STA WCID=1 kontrol edilir. NULL/rezerv WCID/yanlış uzunluk yazma/shift işlemlerine geçmez. Group key için NULL node geçerliliği korunur.
- EAPOL bildirilen toplam gövde uzunluğu header'dan kısa olamaz. Önceki kontrol sizeof(unsigned) çıkarma nedeniyle kısa bildirilen gövdeyi kabul edebiliyordu. Gerçek header ve kontrol ifadeleriyle host test yapıldı. Bu ayrıca bir parser düzeltmesidir; donmanın kanıtlanmış nedeni değildir.
- İlk 8 RUN TX ve RX işlemi, ilk 32 EAPOL descriptor/info/uzunluk kaydı ve anahtar kurulum başlangıç/bitişi loglanır. Parola, PMK/PTK/GTK, paket içeriği veya SSID loglanmaz. TX/RX ve EAPOL detay kayıtları sınırlıdır; yeniden RUN denemesi TX/RX sayaçlarını sıfırlar.
- App/CLI kontrol isteğinin başlamasını, driver çağrısını ve dönüş kodunu stdout'a yazar. Böylece user-space isteğin dönüşü ile kernel ilerlemesi ayrı gözlenir. GUI'nin 0.3.2'deki worker/ana-thread ayrımı korunur.

`complete` logu ilgili fonksiyonun döndüğünü ve kontrol edilen sticky hatanın görülmediğini belirtir. Fiziksel işlemin veya bağlantının başarısı anlamına gelmez. MCU no-wait komutları işlem tamamlanmasını beklemez.

Vendor kod ve lisanslar değişmeden korunur. Yerel proto/PAE fork'ları cloud ve Xcode kaynak listelerinde vendor karşılıklarını dışlar. 0.3.2 kaynakları/arşivleri korunmuştur. EFI, OpenCore, ACPI, SIP ve kalıcı kurulum konumları değiştirilmedi.

## Gerçek kontroller

Normal ve PCI-only kext x86_64 macOS 10.13 hedefiyle derlendi ve ld64 ile MH_KEXT_BUNDLE bağlandı; her hedefte 48 BSD/controller kaynak birimi ve core/kmod nesneleri. Mach-O/kmod metadata, public XNU import ve diagnostic start kontrolleri çalıştırıldı. macOS family export kontrolleri native ortam gerektirir. /System/Library/Frameworks dizini Linux'ta olmadığı için linker uyarısı vardır.

18 host test grubu geçti; loglar verification içinde:

- Core/frame parser, crypto, memchr, PCI, ring, DMA shim, RX ownership, node/MIRA timeout, timeout lifecycle, GUI, kontrol aracı, IRQ/watchdog testleri.
- Gerçek RUN fonksiyonu sağlıklı yol, 10 ayrı alt-adım fault injection, boş rate, NULL BSS, recursive callback ve sticky DMA hatasıyla çalıştırıldı. Eski 0.3.2'nin alt-adım hatasına rağmen ilerlediği negatif kontrolle gösterildi.
- Gerçek net80211 RUN guard, EAPOL uzunluk kontrolü, key validation ve MCU komut fonksiyonu host testleri.

Host shims gerçek IOKit, PCI bus, IRQ, fiziksel DMA veya modem davranışını taklit ederek doğrulanmış sayılmaz. Native Xcode 9.4.1/MacOSX10.13.sdk, kextutil, physical association/WPA2/DHCP/internet yeni sürümde çalıştırılmadı. Donmanın çözüldüğü iddia edilmez.

## Yüklemeden doğrulama

Bu paket otomatik/kalıcı yükleme yapmaz. Önceki Easy Kext Pro/EFI kurulumları yeniden başlatmada eski kopyayı yükleyebilir; bu paket onları değiştirmez. Sadece normal test bundle'ını geçici kopyada doğrulayın:

```bash
sudo ditto "$HOME/Desktop/RT3090Network-test/RT3090Network.kext" /private/tmp/RT3090Network-0.3.3.kext
sudo chown -R root:wheel /private/tmp/RT3090Network-0.3.3.kext
sudo chmod -R u+rwX,go+rX,go-w /private/tmp/RT3090Network-0.3.3.kext
sudo kextutil -n -t /private/tmp/RT3090Network-0.3.3.kext
```

Doğrulama reddedilirse yüklemeyin; çıktıyı koruyun. Güvenlik ayarlarını değiştirmeyin. Başarılı doğrulama donma olmayacağını kanıtlamaz. Normal ve diagnostic bundle kimliği aynıdır; birlikte yüklenmez.

## Gerçek cihazda aşamalı test planı

Önce native doğrulama ve yüklü version kontrolü; ardından Status ve Scan kararlılığı. Connect aşaması hâlâ donma riski taşır; yalnızca önceki doğrulamalardan sonra kontrollü testte ele alınmalıdır. Connect'ten önce dosyaları kaydedin ve kernel logunu ikinci Terminal'de açın. Sonuçları, son görünen begin/complete satırına göre ayırın. Hata varsa ardışık Connect denemeleri yapmayın.

Terminal'de app çıktısı:

```bash
sudo /usr/bin/python -u "$HOME/Desktop/RT3090Network-test/rt3090gui.py" 2>&1 | tee "$HOME/Desktop/RT3090-app-0.3.3.log"
```

Ayrı Terminal'de kernel çıktısı:

```bash
sudo log stream --style syslog --predicate 'process == "kernel" AND eventMessage CONTAINS[c] "RT3090"' 2>&1 | tee "$HOME/Desktop/RT3090-kernel-0.3.3.log"
```

Beklenen ayrımlar: `RUN channel begin`/`complete`, diğer HAL alt adımları, `RUN net80211 begin`/`complete`, ilk TX/RX, `EAPOL RX`, `key install begin`/`complete`. `Request accepted` bağlantı başarısı değildir. WPA2 port authorized olmadan DHCP/Internet doğrulanmaz. Tam donma log dosyasının son satırını diske yazmasını engelleyebilir; görüntüdeki son satır da değerlidir.

## Geri alma

App kapatılır; `sudo kextunload -b org.rt3090.network` yalnızca yüklü kext'i boşaltır. Boşaltma reddedilirse zorlanmaz. Sistem tamamen tepkisizse güç düğmesi son çaredir ve veri kaybı olabilir. Yeni sürümü otomatik/kalıcı kurmayın. Önceden EFI veya sistem klasörüne kurulmuş kopyaların kaldırıldığı bu paket tarafından varsayılmaz. EFI'yi sürücü testi için düzenlemeyin.
