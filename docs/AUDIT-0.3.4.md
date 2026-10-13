# RT3090Network 0.3.4 — proje ve komut incelemesi

## Kapsam ve kanıt sınırı

Mevcut 0.3.3 portu üzerinden çalışıldı; sıfırdan proje veya EFI oluşturulmadı. Aktif PCI/start/enable/stop/cleanup, HAL RUN/TX/RX/DMA/IRQ, BSD queue/timer/node, WPA2 sınır kontrolleri, CLI/GUI, firmware/build/package scriptleri ve test/geri alma komutları incelendi. On ana C++/WPA2 dosyasında Clang static analyzer çalıştırıldı; derlenen bütün normal/tanılama kaynakları derleyiciden geçti. Vendor ağ yığınının bütün olası çalışma yolları tek tek fiziksel olarak doğrulanmadı. Bu nedenle “bütün buglar çözüldü” veya “donma giderildi” denmiyor.

Gözlenen sorunlar: önceki sürümde gerçek AP taraması; Connect sonrası 3→4 logundan sonra tam donma; daha sonra kext yüklü olmasına rağmen boş RT3090Network IORegistry. Son durumun cihazdaki kesin sebebi bilinmiyor. WPA2 aşamasına gelmeden start/matching başarısız olabilir. Kextstat yüklü module bilgisidir; PCI attach/Internet testi değildir.

## 0.3.4 değişiklikleri

1. **Firmware varsayılanı:** network cloud/native build artık paket içindeki checksum/CRC pinli rt2860.bin'i kullanır. Firmware verilmediğinde sessizce firmware'siz network kext üretme yolu giderildi. Eksik/bozuk firmware ile build durur. Binary içeriğinin pinned SHA-256'sı ayrı doğrulanır; pin değiştirilmedi.
2. **Başlatma OOM/panic:** initial BSS allocation NULL durumunda kernel panic yerine kontrollü return. Media init NULL BSS ile devam etmez. Backend attachment, BSS/I/O/queue lock kontrollerini geçirip geçmediğini kontrol eder. Kısmi BSD attachment cleanup'a ait olarak erken işaretlenir; yalnızca tam başarı varsayılmaz.
3. **Queue lock teardown:** management/power-save queue lock'ları daha önce boşaltılıyor ama serbest bırakılmıyordu. Protocol detach artık kısmi initialization'da NULL lock'a girmeden her mevcut lock'u purge/free eder, pointer'ı temizler ve tekrarlı cleanup'a dayanır. Start lock allocation başarısızlığında ilerlemez.
4. **TX queue sahipliği:** dolu queue paket düşürmesine rağmen success döndürüyordu. Yerel RTIfq fork'u gerçek enqueue sonucunu döndürür; hata halinde paketi bir kez tüketir. Controller buna göre ikinci free yapmaz. NULL queue read/dequeue/len işlemleri de korunur. Geçersiz durum ve unauthorized/faulted linkte output reddedilir.
5. **TX ring:** NULL map/descriptor, ring dışı cursor, aşırı queued değeri ve dolu software slot, frame trim/DMA yazısından önce kontrollü EIO ile reddedilir. Bu yoldaki KASSERT/panic kaldırıldı; kontrol atlanmadı.
6. **DMA/MMIO:** NULL CPU pointer veren allocation bzero'ya girmez; allocation serbest bırakılır. NULL BAR pointer/alignment/bounds hatalı region yazıları reddedilir ve sticky fault işaretler. Mbuf chain yüklemesi boyutu erkenden doğrular; cyclic zero-length chain 256 node sınırında reddedilir. <4GiB mapping/end kontrolleri korunur; adres kırpma yapılmadı.
7. **Sticky hata:** hardware/DMA fault kernel enable tarafından otomatik silinip radio restart edilmez. Yeni controller başlangıcında DMA bridge global hata durumu temizlenir. Radio init sonrasında HAL sticky hatası da kontrol edilir; başarısızlık registry'de Running=False/HardwareFailed=True ile yayımlanır.
8. **RUN channel sentinel:** AUTH/ASSOC/RUN'a ANY-channel sentinel ile girilmez. Mevcut RUN fault propagation, EAPOL/key/MCU kontrolleri ve ayrıntılı loglar korunur.
9. **Aygıt/sürücü ayrımı:** başarılı start sonrası version/attached/ilk interface status hemen yayımlanır. Başarısız start, PCI provider üzerinde son hata aşamasını ve denenen sürümü kaydeder. EEPROM read, parse ve RF compatibility aşamaları ayrı kaydedilir. Bu sadece IORegistry durum bilgisidir; EFI DeviceProperties ayarı veya ACPI değişikliği değildir.
10. **CLI/GUI fallback:** controller registry boşsa yalnızca PCI registry okunur. 1814:3090 kartı varsa açık not-attached durumu ve mevcut start error gösterilir; yoksa açık error. Gerçek controller/interface olmadan radio request gönderilmez. XML schema hatası anlaşılır error olur. Sahte controller veya ağ sonucu oluşturulmaz.
11. **Komutlar:** rt3090-test.command check/load/unload/status/log işlemleri sunar; default check hiçbir kext yüklemez. check/load temiz mktemp staging kullanır, ownership/permissions düzeltir. load mevcut module varsa durur; validation hata kodu yüklemeyi keser. Betik otomatik unload, EFI/SIP/Extensions/cache düzenlemesi yapmaz. Sadece kendi temp dizinini temizler. Native build'in gösterdiği kext yolu tırnaklıdır; ping bekleme sınırı vardır. Eski README/NETWORK sürüm karışıklıkları giderildi; RECOVERY güncellendi.
12. **Ek kaynak düzeltmeleri:** native firmware/build ayarları, typed RT node allocation (base node'a doğru dönüş) ve fallback-rate unsigned shift kontrol edildi. Vendor/lisans dosyaları korunur; değiştirilen BSD queue ayrı yerel fork olarak seçilir.

## Gerçek testler

28 host test grubu: core/beacon parser, crypto, memchr, PCI, ring, DMA bridge, RX ownership, node/MIRA init, timeout lifecycle, GUI request, controller helpers, IRQ/watchdog, RUN transition/preflight, EAPOL bounds, key validation, MCU commands, BSS allocation, queue ownership, output ownership, PCI registry fallback, manual shell commands, TX preflight, protocol cleanup, connection progress, gerçek EAPOL M1/M2/M4 kontrol akışı ve sürücü→GUI status aktarımı.

Host ASan/UBSan testleri gerçek kaynak fonksiyonları veya ilgili gerçek preflight/guard bölümlerini kontrollü shims ile çalıştırır. TX preflight testi tam TX aktarımı değildir. Command testi gerçek shell akışını macOS-only komut stand-in'leriyle yürütür; native kextutil çalıştırılmaz. Status testi gerçek XML parse/recursive lookup kullanır; IOKit çağrıları mock'tur. GUI fake Tk ile thread ayrımını sınar; native GUI testi değildir.

Normal ve diagnostic kext x86_64 High Sierra hedefiyle cross-compile/link edildi. Her hedef 49 BSD/controller kaynak birimi ve core/kmod nesneleri içerir. Mach-O MH_KEXT_BUNDLE, kmod version/identifier, forbidden/private imports, XNU public export ve diagnostic start kontrolleri çalıştırıldı. Firmware pin, package binary hash, app/CLI kaynak eşleşmesi ve bundle version kontrol edilir. Linux'ta /System/Library/Frameworks bulunmaması linker uyarısıdır.

Clang analyzer on ana C++/WPA2 dosyasında tamamlandı. Kalan raporlar dead-store (debug makrosu kullanılmayan değerler/vendor bitfield/ilk stage ataması) uyarılarıdır. EEPROM register okumaları yan etki taşıyabileceği için sadece debug kullanılmıyor diye kaldırılmadı. Allocation-size uyarısının extended RT node/base-node ilişkisi doğru typed dönüşle netleştirildi. Static analysis donma/race/ABI güvenliği kanıtlamaz. Raw raporlar verification/static-analysis içindedir.

## Açık doğrulama gereksinimleri

- macOS 10.13.6 üzerinde gerçek kextutil dependency/ABI/policy kontrolü ve start logu.
- Karta özel EEPROM/RF/radio işlemleri, firmware MCU yanıtları, gerçek IRQ/DMA timing.
- RUN→EAPOL→key install→authorized port, DHCP/RT3090 üzerinden trafik.
- Sleep/wake ve yoğun uzun süreli trafik güvenliği tamamlanmış olarak sunulmaz.
- Yeni sürümün önceki Connect donmasını giderdiği veya bütün vendor yollarının hatasız olduğu doğrulanmadı. Native Xcode 9.4.1/MacOSX10.13.sdk ortamı cloud'da yok.

Güncel geçici komutlar NETWORK.md içindedir. Önce check ve yalnızca Status; hardware fault/not-attached durumunda Connect/Scan gönderilmez. Yeni sürümü Easy Kext Pro/EFI ile kalıcı kurmak bu geliştirme paketinin test akışı değildir.

WPA2:0 gözlemi için ek kaynak analizi/düzeltmeler: [WPA2-0.3.4.md](WPA2-0.3.4.md). Bu değişiklikler aynı teslimattaki 0.3.4 kaynağına dahildir.
