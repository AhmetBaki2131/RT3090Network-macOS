> Tarihsel aşama raporu. Güncel sürüm/komutlar README.md, NETWORK.md ve AUDIT-0.3.4.md içindedir; aşağıdaki eski yükleme komutlarını güncel pakete uygulamayın.

# RT3090Network 0.3.2 — Connect donması için kaynak düzeltmeleri

Bu sürüm 0.3.1 kaynaklarının devamıdır. Hem uygulama hem kext değiştirildi. Donmanın fiziksel cihazdaki kesin nedeni ve yeni sürümün Wi-Fi bağlantısı doğrulanmadı. Analytics dosyası panic/backtrace içermediği için bir hata adresiyle eşleştirme yapılamıyor. Bütün hataların giderildiği iddia edilmiyor.

## Kanıtlanan bellek hataları

1. `ieee80211_node_set_timeouts`: 16 adet 64-bit pointer içeren 128 baytlık dizi `sizeof(array) * nitems(array)` ile 2.048 bayt sıfırlanıyordu. Node kopyalama/başlatma sırasında komşu bellek bozulabilir. Yerel `port/ieee80211_node.c` fork'u yalnızca gerçek dizi boyutunu temizler.
2. `ieee80211_mira_node_init`: iki pointer içeren 16 baytlık dizi için 32 bayt temizleme aynı şekilde düzeltildi. HT/MIRA yolunun kullanılması bu kartın mevcut çalışma yolunda ayrıca doğrulanmalıdır.
3. RX aktarımı: `inputPacket` mülkiyetini aldıktan sonra paketin nextpkt alanı okunuyordu; paketler NULL nextpkt koşuluyla teslim edilmiyordu. `RTMbuf.cpp` artık önce dequeue yapar. Arayüz yoksa paket düşürülür; panic tetiklenmez.

Vendor kaynakları ve lisansları korundu; cloud ve Xcode derlemeleri yerel fork'ları seçer. Testler eski node ve MIRA kodunu ayrı çalıştırıp ASan heap-buffer-overflow yakaladı. Yeni gerçek fonksiyonlar ASan/UBSan testlerinden geçti. RX eski kodu aynı testte bağlantı assertion'ında başarısız oldu.

## Diğer düzeltmeler

- CTimeout reset sırasında eski timeout iptal edilir. İptal edilmiş/geçersiz callback çalıştırılmaz. Callback kendi timeout nesnesini serbest bıraksa bile dönüşe kadar owner retain edilir. Free, timer'ı cancel/disable edip event source'u kaldırır; NULL workloop reddedilir.
- PBKDF2 4.096 iterasyonu IRQ ve timer işlerinin kullandığı command gate dışında çalışır. PMK gate içinde uygulanır; geçici password ve PMK temizlenir. Kök kullanıcı yetki kontrolü korunur.
- IRQ filtresi etkin interrupt maskesini kontrol eder. Bir handler DMA/I/O hatası bildirdiğinde sonraki handler'lar çalıştırılmaz.
- TX timeout sürücüyü otomatik yeniden başlatma döngüsüne sokmaz; durur ve hata işaretler. IRQ/tick bu işareti kontrol eder. Yeni `RT3090HardwareFailed` özelliği kontrol aracına görünür; app/CLI hata sonrası Connect'i otomatik yeniden denemez.
- TX kuyruk boşaltma çağrısı 128 denemeyle sınırlanır; sağlıklı durumda tick ve tamamlanma IRQ'ları kalan işi sürdürür.
- Kanal tablosu araması sınırlıdır; RT3090 için 1..14 dışındaki kanallar panic yerine hata oluşturur. NULL kanal reddedilir.
- Rate dizisi sayısı/kuralları ve TX kuyruk/fixed-rate indeksleri erişimden önce kontrol edilir. Son geçerli legacy rate indeksi aramaya dahildir.
- RX ring önceki indeks hesabı wrap durumunda geçerli ring indeksi üretir.
- Güç nibble kaydırması uint32_t kullanır; signed shift undefined behavior kaldırılır.
- GUI Scan, Connect, Disconnect, Status, DHCP ve Check işlemlerini worker üzerinde yürütür; bütün Tk çağrıları ana thread'dedir. Bekleyen işlem bitmeden ikinci istek gönderilmez. GUI'nin donması ile tüm sistemin donması ayrı sorunlardır: bu değişiklik kernel donmasının giderildiğini tek başına kanıtlamaz.
- CF request oluştururken kısmi allocation hatasında başarılı önceki allocation'lar da temizlenir.
- Durum geçişleri parola/SSID içermeden kernel loguna yazılır.

## Gerçek testler ve sınırları

Cloud: x86_64 High Sierra hedefi için normal ve PCI tanılama kext'i derlenip ld64 ile bağlandı; her biri 48 BSD/controller kaynak birimi ve core/kmod nesneleri içerir. Mach-O ve kmod metadata kontrolleri, public XNU import karşılaştırması çalıştırıldı. Linux linker'ın mevcut olmayan /System/Library/Frameworks yolu uyarısı native framework testi değildir.

Host ASan/UBSan: core/frame parser, crypto, memchr, PCI, ring, DMA bridge shim, RX ownership, gerçek node/MIRA initializer, gerçek timeout lifecycle ve IRQ/watchdog fault dispatch testleri. GUI testi gerçek GUI modülünü fake Tk ve fake kontrol modülüyle çalıştırır; istek sıralaması ve Tk ana-thread kuralını sınar. Python 2 sözdizimi grammar kontrolü yapıldı; cloud'da Python 2.7 runtime ve macOS Tk yok.

MacOSX10.13.sdk/Xcode 9.4.1 native derlemesi, High Sierra kextutil, fiziksel DMA/IRQ, radyo, authentication/association, WPA2 4-way handshake, DHCP ve internet bu yeni sürümde yapılmadı. Public XNU export karşılaştırması hedefin IOPCIFamily/IONetworkingFamily binary export kontrolünün yerini tutmaz. Eski sürümde kullanıcı gerçek ağ taraması gördü; bunu 0.3.2 doğrulaması olarak saymıyoruz.

## Geçici doğrulama ve kontrollü test

EFI/OpenCore/ACPI/SMBIOS/SIP ayarlarını değiştirmeyin. App kext yüklemez ve kurmaz. Normal ve diagnostic kext'leri aynı bundle identifier kullanır; birlikte yüklenmez.

Önce app'i kapatın; eski sürücüyü yalnızca geçici yüklendiyse boşaltın:

```bash
sudo kextunload -b org.rt3090.network
kextstat -b org.rt3090.network
```

Boşaltma hata verirse zorlamayın; restart sonrası sürüm ve yüklenme durumunu tekrar kontrol edin. Paketi Desktop'a açtıktan sonra geçici kopyada izinleri düzeltip önce yüklemeden doğrulayın:

```bash
sudo ditto "$HOME/Desktop/RT3090Network-test/RT3090Network.kext" /private/tmp/RT3090Network-0.3.2.kext
sudo chown -R root:wheel /private/tmp/RT3090Network-0.3.2.kext
sudo chmod -R u+rwX,go+rX,go-w /private/tmp/RT3090Network-0.3.2.kext
sudo kextutil -n -t /private/tmp/RT3090Network-0.3.2.kext
```

Sembol/izin/signature/security hataları varsa durun ve çıktıyı koruyun. SIP'i değiştirmeyin. Başarılı doğrulama Wi-Fi başarısı değildir. Yükleme ancak bu adım başarılıysa ayrı, elle yapılır:

```bash
sudo kextutil -v 6 /private/tmp/RT3090Network-0.3.2.kext
kextstat -b org.rt3090.network
```

0.3.2 göründüğünü kontrol edin. Önce Status, sonra Scan; sistem ve tarama kararlı olmadan Connect'e geçmeyin. Kernel loglarını ikinci Terminal'de açık tutun:

```bash
log stream --style syslog --predicate 'process == "kernel" AND eventMessage CONTAINS "RT3090"'
```

Connect kabulü bağlantı başarısı değildir. Association/supplicant durumları ve Controlled port authorized izlenmeli. Yetkilendirme gerçekleşmeden DHCP veya Internet testi başarı göstermez. Hata veya HardwareFailed çıktısında tekrar Connect göndermeyin; Status, log ve mevcut panic raporunu kaydedin. Durum geçişi logu hangi aşamaya erişildiğini ayırmaya yardımcı olur.

## Geri alma

App'i kapatıp `sudo kextunload -b org.rt3090.network` çalıştırın. Bu paket sürücüyü kalıcı yere kopyalamaz, cache/EFI değiştirmez. Geçici testin geri alınması EFI değişikliği gerektirmez. Sistem tamamen donarsa veri kaybı ihtimalini dikkate alarak güç düğmesiyle kapatma son çaredir. Yeniden açınca yeni sürücüyü tekrar yüklemeyin. Önceden kendi başınıza kalıcı kurulum yaptıysanız onun konumu bu paketten belirlenemez; mevcut çalışan EFI'yi bu test için düzenlemeyin.
