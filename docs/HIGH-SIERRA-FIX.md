# High Sierra sembol düzeltmesi — 0.2.1

> Tarihsel kayıt. Güncel 0.2.2 PCI-only akışı NETWORK.md ve SAFETY-0.2.2.md içindedir.
> Buradaki eski hardware-mode ilerleme önerileri güncel tanı binary'sine uygulanmaz.

Hedef: HP Pavilion dv6, 1814:3090 / 103C:1453 / REV_00, Core i5-M460,
macOS 10.13.6, OpenCore 1.0.8, MacBookPro6,1. EFI ve SIP ayarları değiştirilmedi.

## Kaynak araması ve değişiklik

Eski iki çağrı `port/RT3090Network.cpp` satır 232 ve 253'teydi.
Tüm kaynak snapshot'ları dahil aramada ayrıca MacKernelSDK
`Headers/libkern/libkern.h:156` memchr bildirimi ve `Headers/sys/kauth.h:272`
kauth_cred_issuser bildirimi bulunur. Bu upstream bildirimler değiştirilmedi.
Yeni kaynakta ilk çağrı rt_memchr, ikincisi kauth_cred_getuid ile değiştirilmiştir.
Derleme logları yanındaki forbidden-symbol-search.log başlıklar ve doğrulama
script'indeki bilerek tutulan yasaklı isimleri de içerir; bunlar çağrı değildir.

XNU xnu-4570.71.2 commit 925687e1592f2ca08052622e35d1f61df4ad3c85:
`config/BSDKernel.exports:310` kauth_cred_get, `:319` kauth_cred_getuid;
kauth_cred_issuser yalnızca `Private.exports:521` ve
`Unsupported.exports:92` içindedir. Public export listelerinde memchr yoktur.
Bu export dosyaları kaynak ZIP'indeki research/xnu-4570.71.2 içindedir.
Bir başlık bildirimi veya kernel implementasyonu üçüncü taraf KPI izni değildir.

Root kontrolü `kauth_cred_getuid(kauth_cred_get()) != 0` ise isteği reddeder.
Bu, mevcut işlemin etkin UID'sini kullanır. Kontrol kaldırılmadı; kullanıcıdan
alınan UID veya IORegistry property değeri güvenilir kimlik olarak kullanılmaz.

`src/rt3090_core.c:314` rt_memchr caller-owned buffer'da en fazla n byte arar.
Null/sıfır uzunluk ve uintptr_t adres toplamı taşması durumunda NULL döner.
Geçerli uzunluk ve okunabilir memory sağlamak caller'ın sorumluluğudur;
helper bilinmeyen pointer'ın gerçekten mapped olduğunu doğrulayamaz. Parola
çağrısındaki buffer 64 byte stack array, n önceden 8..63 olarak sınırlandırılmıştır.
10 ASan/UBSan testi null, sıfır, ilk/son eşleşme, bulunamama, signed byte dönüşümü
ve taşan aralığı kapsar. Kernel libc memchr bağımlılığı kalmaz.

## Tüm importların denetimi

`scripts/audit-high-sierra-imports.py` gerçek yeni Mach-O importlarını public
XNU x86_64 export listeleriyle karşılaştırır. 496 import: 357 public XNU
export eşleşmesi, 139 family kext import'u, 0 sınıflandırılmamış import.
Family sınıflandırması o sembolün hedef cihazda export edildiği kanıtı değildir.
139 sembolün tamamı JSON log'da ayrı listelenmiştir; installed High Sierra
IOPCIFamily/IONetworkingFamily binary export'ları burada bulunmadığı için
native kextutil ile doğrulanmalıdır. Bu eksik kontrol gizlenmez.

Yapısal verifier iki eski import'u ayrıca reddeder. Cross-link'te kernel
importlarının undefined olması normaldir; hedef kernel/kext export'larına
bağlanmaları macOS kxld safhasında gerekir. Linker dynamic_lookup seçeneği
native validation yerine başarılı yükleme kanıtı olarak kullanılmadı.

## Derleme ayarları ve sınır

SDKROOT=macosx10.13, deployment=10.13, ARCHS=x86_64; native product type
kernel-extension. build-network-macos.sh SDK'nın kurulu olduğunu xcrun ile
kontrol eder ve xcodebuild'e -sdk macosx10.13 geçirir. MacOSX10.13.sdk ve
Xcode 9.4.1 bu Linux ortamında yoktur; bu oturumdaki build Clang 19,
MacKernelSDK snapshot ve Apple ld64 portuyla cross-build'dir. Native Xcode
9.4.1 derlemesi yapılmış olarak raporlanmaz. Eski header snapshot'ını SDK
seçimiyle aynı şey olarak sunmuyoruz; native ABI hâlâ kontrol edilmelidir.

Mach-O x86_64 MH_KEXT_BUNDLE, kmod metadata, constructor/destructor bölümleri
kontrol edildi. InfoNetwork.plist: IONetworkingFamily 1.5.0, IOPCIFamily 1.7,
BSD/IOKit/libkern/Mach KPI 8.0.0 minimum bağımlılıkları korunmuştur. Bu sayılar
kernel API mevcutmuş gibi göstermek için yükseltilmedi; hedef sistemin bunları
karşılaması kextutil tarafından kontrol edilir.

DMA mapping veya ring kaynakları değiştirilmedi. IODMACommand OutputHost32,
32-bit adres + uzunluk denetimi ve başarısız mapping reddi korunur; adresleri
32-bit'e kırparak uygunmuş gibi gösterme yoktur.

## İlk cihaz kontrolü: yükleme yok

Yeni test ZIP'ini açın; RT3090Network-test klasörünü Masaüstü'ne koyun:

```sh
sudo kextutil -n -t "$HOME/Desktop/RT3090Network-test/RT3090Network.kext" 2>&1 | tee "$HOME/Desktop/rt3090-check.txt"
```

Eski kext'i yeni dosyayla karıştırmayın; bu sürüm 0.2.1'dir. İmzasız build'in
-67062 veya Code Signing Failure satırları gizlenmez. Signing/policy hatasıyla
symbol link hatası farklıdır; uygun doğrulama sağlanmadan yüklemeye geçmeyin.
Bu paket EFI, OpenCore config veya SIP'i otomatik değiştiren script içermez.

Native doğrulama başarılı olursa NETWORK.md'deki şartlarla aşamalar:
PCI/service attach → firmware/MCU → RF/BBP/radyo → gerçek scan sonuçları →
association/EAPOL/WPA2 yetkilendirme → DHCP ve RT3090 arayüzünden trafik.
Her aşama kendi çıktı/log'uyla kanıtlanır. Bu yeni binary'de hiçbiri gerçek
kartta test edilmedi. Eski kullanıcı çıktısı yalnızca önceki link hatalarını
kanıtlar. Yeni başarılı kextutil sonucu bile çalışan Wi-Fi kanıtı değildir.
Kurtarma ve staging kaldırma adımları NETWORK.md içindedir.
