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


# WPA2 durum ve EAPOL incelemesi — 0.3.4

## `WPA2: 0` nereden geliyor?

Kaynak zinciri: GUI `render()` → kontrol aracı `snapshot()` → IORegistry `RT3090WPA2SupplicantState` → controller `publishStatus()` → `chip.sc_ic.ic_bss->ni_rsn_supp_state`.

Bu bir sinyal/güvenlik türü veya bağlantı başarılı flag'i değildir. `ieee80211_node.h` supplicant enum'u:

| Sayı | Gösterilen ad | Kaynak anlamı |
|---|---|---|
| 0 | INITIALIZE | Henüz handshake mesajı beklemiyor; SCAN/ilk AUTH sırasında normal olabilir |
| 1 | WAIT_M1 | Association RSN etkinse M1 bekleniyor |
| 2 | M2_QUEUED_WAIT_M3 | M1 işlenip M2 gönderim kuyruğuna kabul edildi; M3 bekleniyor |
| 3 | M4_QUEUED_KEYS_PENDING | M3 işlenip M4 kuyruğa kabul edildi; bu değer tek başına port authorization değildir |

`ControlledPortAuthorized`, BSS `ni_port_valid` alanı, RUN/link/running ve fault kontrolleriyle birlikte ayrı yayınlanır. RUN dışına çıkınca port kapatılır; stop/initialization failure stale true bırakmaz. DHCP/Check yalnızca bu alan true ise ilerler; RUN veya supplicant=3 internet kanıtı değildir.

## Neden hep 0 görülmüş olabilir?

- Önceki GUI, ilk/manuel Status dışında otomatik durum okumuyordu. Scan/Connect isteğini kabul mesajı durum değişkenlerinin güncellendiğini göstermiyordu. Canlı alan yerine eski snapshot görülebiliyordu; düzeltildi.
- Driver status yayınlama, scan-results array allocation'ına bağlıydı. Bu allocation başarısızsa connection status da yayınlanmıyordu. `publishStatus()` ayrıldı ve scan allocation'dan önce çalışır.
- Association response, RSN etkinse state=1 yapar. M1, state=0 iken bilinçli reddedilir. RUN'a geçilip hâlâ 0 görülüyorsa RSN flag'i, state yayını ve son tamamlanan kernel aşaması ayrı kontrol edilmelidir. Bu sürüm RSNEnabled, seçilen proto/cipher/AKM alanlarını yayınlar.
- Önceki tam donmada tick/GUI yenilemesi çalışamamış olabilir; eski 0 değerinin donma anındaki gerçek BSS değeri olduğu kanıtlanamaz.

Kullanıcının cihazındaki kesin sebep log/backtrace ile eşleştirilmedi. `0` görünce zorla `1` yazma veya sahte başarı yapılmadı.

## Authentication/Association/RUN

Auth open response ve association response peer status kodları ayrı loglanır. IEEE peer status ile proje connection error kodu ayrı alanlardır. Peer status varsayılan 0 olabilir; response logu olmadan bu değer authentication başarısı sayılmaz. RUN başlatmanın mevcut alt-adım/error propagation kontrolleri korunur. Yeni model, explicit Connect için faz ilerlemesini izler. SCAN yaklaşık 30, AUTH/ASSOC yaklaşık 15, M1/M3 yaklaşık 15, M4 sonrası authorization yaklaşık 5 timer tick'inde ilerlemezse allow_join kapanır ve INIT istenir. Bunlar responsive workloop üzerinde yaklaşık saniyelerdir; sistem/hardware bus tamamen donarsa timer kurtaramaz.

## Gerçek EAPOL kod yolu

RX: PCI RX ring → rt2860_rx_intr → ieee80211_inputm → Ethernet decap → ETHERTYPE_PAE dispatch → ieee80211_eapol_key_input → M1 veya M3 handler.

TX: M2/M4 builder → ieee80211_send_eapol_key → BSD if_snd queue → rt2860_start/802.11 encap → rt2860_tx → DMA descriptors → TX doorbell. Port henüz yetkilendirilmemişken EAPOL bu iç yol üzerinden gönderilir; normal Ethernet/DHCP çıkışı kapalı kalır.

Değişiklikler:

- M2/M4 supplicant state artık allocation ve queue başarısızlığından önce ilerletilmez. Queue success sonrasında ilerler. Başarısız allocation/enqueue sayılır ve loglanır.
- M1/M3 handler girişleri, M2/M4 queue sonuçları, key install ve MIC hataları ayrı kaydedilir. Paket başına detay logları ilk 32 olayla sınırlanır; sayaçlar devam eder. M1 INITIALIZE'da gelirse explicit error=203 olur. M1 replay koruması kaldırılmadı.
- M1 geçici derived PTK, synchronous M2 oluşturma/gönderme dönüşünden sonra silinir. Parola/PMK/PTK/GTK/nonce loglanmaz.
- Gerçek LLC/SNAP 0x888e frame'i için TX doorbell'e kadar ulaşma ayrı sayaçtır. Bu sayaç modem ACK'ini veya over-the-air başarıyı kanıtlamaz.
- GUI her yaklaşık saniyede arka planda Status okur; çalışan istekle çakışmaz. Scan listesinde BSSID seçimini korur. Read error sonrası sürekli modal popup üretmemek için otomatik polling durur; manual Status tekrar açar.

## Status alanları

- RT3090EAPOLM1RX / RT3090EAPOLM3RX: ilgili handler'a ulaşmış mesajlar; valid/MIC-authenticated oldukları anlamına gelmez.
- RT3090EAPOLM2Queued / RT3090EAPOLM4Queued: başarılı queue transferleri; fiziksel TX ACK değildir.
- RT3090EAPOLTXFailures: M2/M4 allocation/queue hataları.
- RT3090EAPOLHardwareTXSubmitted: EAPOL olarak tanınmış frame'in TX doorbell yazısına ulaşması; gerçek RF TX/ACK doğrulanmadı.
- RT3090KeyInstallCount: driver callback'in başarı döndürdüğü key install sayısı; hardware kripto doğrulaması değildir.
- RT3090BadMICCount, RT3090PeerStatusCode, RT3090ConnectionErrorCode, phase/tick, RSN/proto/cipher/AKM: hata aşamasını ayırır.

## Hata kodları

| Kod | Anlam |
|---|---|
| 101 | Scan süresi doldu |
| 102 | Authentication ilerlemedi |
| 103 | Association ilerlemedi |
| 104 | M1 gelmedi/işlenemedi |
| 105 | M3 gelmedi/işlenemedi |
| 106 | Controlled port yetkilendirilmedi |
| 201 / 202 | AP authentication / association reddetti; peer status ayrıca gösterilir |
| 203 | M1 INITIALIZE durumunda reddedildi |
| 301 / 302 | M2 / M4 allocation veya queue başarısız |
| 303 | MIC kontrolü başarısız; sadece yanlış parola demek değildir |
| 304 | Key install callback hata döndürdü |

Ayrıntılı son hata timeout'a kadar korunur. Başarılı port authorization error alanını temizler. Asenkron başarısızlık, önce kabul edilmiş control çağrısının dönüşünü geriye dönük değiştiremez; Status/log üzerinden raporlanır. Parametre/attach/radio başlangıç hataları control çağrısında hemen hata döner. HardwareFailed/sticky DMA hata kontrolleri ayrı korunur.

## Çalıştırılan testler

- Gerçek M1/M2/M4 fonksiyonları host testinde çalıştırıldı. INITIALIZE/replay M1 reddi, M1→M2, queue/OOM başarısızlığı, state'in yanlış ilerlememesi, sayaçlar ve portun kendiliğinden açılmaması doğrulandı. Crypto/random/send helper'ları bu testte mock'tur; tam 4-way handshake testi değildir. Ayrı mevcut crypto testleri gerçek PBKDF2/HMAC/AES/key-wrap kodunu sınar.
- Gerçek publish kaynak bölümü → XML serialization → gerçek CLI snapshot → gerçek GUI render (fake Tk) 0/1/2/3 ve port authorization değerleriyle test edildi. Native IOKit çağrısı/GUI testi değildir.
- Progress model auth/assoc/M1/M3 timeout, phase değişimi, queue/MIC/peer/key failure, success/cancel yollarıyla sınandı.
- Toplam 28 host test grubu ve normal/diagnostic cross-build çalıştırıldı. Native High Sierra kextutil, fiziksel authentication/association, M1/M3 RX, M2/M4 RF TX, full handshake, DHCP ve Internet yeni sürümde doğrulanmadı.

Güncel geçici validation/test komutları NETWORK.md içindedir. Önce loaded version + attach + Status/Scan; ardından ancak doğrulama/kararlılık sağlandıysa kontrollü bağlantı aşaması. Önceki tam donmanın giderildiği garanti edilmez. EFI/OpenCore/SIP değiştirilmedi.


## Kapsam sınırı
Bu rapor tespit edilen sorunları kapsar; bütün vendor dosyalarının her hata yolunun kanıtlandığı anlamına gelmez. Sleep/wake, yeniden anahtarlama, replay korumasının donanım tarafı, uzun trafik ve fiziksel reconnect doğrulanmadı. Gerçek Connect donmasının kesin kök nedeni henüz bilinmiyor.
