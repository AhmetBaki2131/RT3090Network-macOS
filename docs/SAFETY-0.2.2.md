# 0.2.2 geliştirme ve risk inceleme raporu

Kullanıcı son EFI denemesinin kernel panic oluşturduğunu bildirdi. Panic
backtrace olmadan sebep belirlenmedi. Bu görev yalnızca sürücü dosyalarını
ve testlerini değiştirdi; EFI/OpenCore/ACPI/SSDT/boot argümanı/SIP değişmedi.
Yeni EFI ZIP'i oluşturulmadı. Önceki 0.2.1 çıktıları ayrı arşivde korundu.

## Neden önce PCI-only?

0.2.1 start() EEPROM/MMIO, BSD attach, DMA allocations ve ardından interrupt
ve interface yaşam döngüsünü tek aşamada gerçekleştiriyordu. Hata kaydı yeterli
olmadığı için boş ioreg sonucu tek bir aşamayı işaret etmiyordu. Üstelik eski
-start gate'i boot argümanına bağlıydı. Yeni artifact'te compile-time default
PCI-only, argümansız probe/start vardır. Runtime ile tam ağ moduna geçiş yok.

Diag branch: configRead16/configRead8; IORegistry özellikleri; registerService.
PCI open/close, PCI command write, BAR map/MMIO, EEPROM, firmware, ring, IRQ ve
interface çağrıları start branch'inden preprocessor ile çıkarılır. pci retain
cleanup'ta release edilir; opened=false olduğundan cleanup PCI yazısı yapmaz.
Framework superclass/init/virtual ABI ve PCI config read cihazda hâlâ risk
alanlarıdır. Bu mod risksiz veya donanımda başarılı olarak sunulmaz.

## PCI personality düzeltmesi

Önceki InfoNetwork.plist IOPCISubsystemMatch kullanıyordu. İncelenen Apple
IOPCIFamily-320.1.1 IOPCIBridge::pciMatchNub() tablosunda primary,
secondary ve class anahtarları vardır; subsystem register 0x2c için
IOPCISecondaryMatch kullanılır. MacKernelSDK IOPCIDevice.h açıklaması da
bu anahtarı belirtir. Yeni plist primary=0x30901814,
secondary=0x1453103C içerir. Eski yanlış anahtarın boş ioreg'nin tek nedeni
olduğu kanıtlanmadı; sürücü zaten start içinde kimlik kontrolü yapıyordu.

## Kaynakta düzeltilen somut riskler

- PCI probe eklendi; aynı vendor/device/subsystem predicate'i start ve probe
  kontrolünden geçer. Başlangıç ret safhaları loglanır.
- BSD detach eski kodda interface release sonrasında idi; timer/callback
  ifp->iface pointer'ı geçersiz kalabilirdi. Detach sırası değiştirildi,
  teardown command gate üzerinden serileştirilir.
- PCI açılmış ama aktif aygıt reddedilmişse cleanup gereksiz bus-master
  disable yazısı yapıyordu. Yalnızca hardwareClaimed durumunda yapılır.
- CTimeout::timeout_set unchecked new sonucunu dereference ediyordu.
  Yerel RTTimeout fork'unda new/init ve timer event-source kurma hataları
  denetlenir, field'lar başlatılır ve başarısız source release edilir.
- ieee80211_ifattach() unchecked sockaddr allocation sonrası LLADDR memcpy
  yapıyordu; queue allocation da kontrolsüzdü. Yerel fork erken fail/unwind
  yapar ve attachhook network_attached=true yapmadan çıkabilir.
- rt2860_tx() NULL packet/node/data_pool ve header/rate sınırlarını kontrol
  etmiyordu. Pullup sonrası caller packet güncellenir; kısa header, payload
  üst sınırı, rate table/index sınırları reddedilir.

Bu bulgular hipotetik genel uyarılar değil, kaynakta gözlenen kontrol
eksiklikleridir. Ancak hiçbiri önceki donanım panic'ine eşleştirilmiş değildir.
Timer/mbuf/DMA kernel yollarının runtime hata enjeksiyonu burada yapılamadı.

## DMA/IRQ/firmware sınırı

32 bit IODMACommand ve segment toplamı/adres sonu denetimleri korunur.
Device write sonrası posted flush ve range check korunur. DMA idle timeout
buffer quarantine davranışı sürer. TX/RX descriptor adresleri yalnızca
başarılı 32-bit mapping sonrası kullanılır; adres kırpma çözüm olarak eklenmez.
Tüm bu donanım işlemleri current artifact PCI-only start'ında yapılmaz.

WPA2 EAPOL/CCMP/scan kodu kaynakta kalır; firmware/IRQ/scan gerçeği PCI tanı
başarısı ve panic analizi sonrasında ayrı aşamalarla test edilmelidir.
49 sayısı önceki konuşmada kullanılan sayıydı; güncel script 48 network/compat
translation unit + core ve kmod olmak üzere 50 object link eder. Her iki
preprocessor modunda 48 network/compat dosyası ayrı compile kontrolünden geçti.

## Gerçek çalıştırılan kontroller

Build/test logları paketin verification dizinindedir. Cross-build Clang 19 +
MacKernelSDK + gerçek ld64-409.12; native MacOSX10.13.sdk/Xcode 9.4.1 yoktur.
Default PCI-only binary x86_64 MH_KEXT_BUNDLE, init/term ve kmod metadata
kontrolünden geçti. Forbidden memchr/kauth_cred_issuser import'ları yok.
Public XNU export audit bütün importları sınıflandırır; family kext import'ları
native High Sierra validation gerektirir. Yapı kontrolü macOS kxld yerine geçmez.

Compiler-preprocessed start audit hardware çağrılarının default method'da
yokluğunu kontrol eder; deneysel mode'da bunları bulması negatif kontroldür.
Bu static source-path kontrolü superclass davranışı veya runtime API garanti
vermez. Host PCI predicate testi 7 doğru/yanlış kimlik case'i içerir; gerçek
PCI config'e erişmez. Native probe/start, unload ve new diagnostic CLI runtime
bu bulut ortamından test edilmedi. Önceki başarılı kextutil sonucu sadece
önceki sürüme aittir; 0.2.2 için tekrar -n -t gerekir.

Yeni PCI-only artifact'in internet sağladığı iddia edilmez. Ağ işlevlerinin
runtime kapalı olması bu tanılama aşaması için kullanıcının açık talebidir.
