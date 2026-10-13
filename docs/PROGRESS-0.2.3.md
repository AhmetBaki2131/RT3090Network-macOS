# RT3090Network 0.2.3 — ağ veri yolu geliştirmesi

Kullanıcı panic'in yanlış hazırlanmış EFI'den kaynaklandığını belirtti.
Panic bu görevde sürücü hatası olarak kabul edilmedi; panic raporu yeni
çalışmanın ön koşulu yapılmadı. EFI, OpenCore, ACPI, boot argümanı ve SIP
ayarları değiştirilmedi. Çalışma mevcut sürücü kaynaklarından devam etti.

Donanım: HP dv6, Intel i5-M460, High Sierra 10.13.6 x86_64,
1814:3090 / 103C:1453 / REV_00. Windows konum yolu
PCIROOT(0)#PCI(1C00)#PCI(0000) rapora ve diagnostic registry hint'ine eklenir.
PciRoot(0x0)/Pci(0x1c,0x0)/Pci(0x0,0x0) aday macOS biçimidir; actual macOS
IORegistry yolu ölçülmedi, eşleşmeyi bu tahmini yola bağlamıyoruz.

## Gerçek kod değişiklikleri

- RX replacement önce ayrı bir DMA map'e tamamen yüklenir. Başarısız
  allocation/mapping eski map'i geçerli bırakır; yeni mbuf/map temizlenir,
  paket düşürülür. Eski map'i kaldırıp geri yüklemeye çalışma ve bu geri
  yükleme başarısızlığındaki explicit panic kaldırıldı.
- TX/RX completion index register'ları ring kapasitesine göre kontrol edilir.
  0xffffffff veya kapasite dışı değerler endless wrap döngüsüne sokulmaz.
- TX completed distance, queued descriptor sayısını aşamaz; counter underflow
  ve donanımdan bildirilen geçersiz completion reddedilir.
- TX status FIFO okuması bounded; 0xffffffff/128'den fazla kesintisiz status
  hardware error olur. Böylece stuck MMIO read CPU döngüsünü kilitlemez.
- Coherent-interrupt recovery başarısızlığı artık kaydedilir. IRQ hardware
  error'da controller stop yoluna gider, interrupt mask yeniden açılmaz.
- WPA2 PBKDF2 error durumunda geçici PMK sıfırlanır; scan/join kodları korunur.
- Network branch registry'de network-experimental mode'unu belirtir;
  superclass start başarısızlığı loglanır.

Bunlar gerçek runtime senaryoları burada gözlenmeden yapılan kaynak
düzeltmeleridir. Windows device status bunları veya macOS scan/WPA2'yi doğrulamaz.

## Çalıştırılan testler

Default diagnostic 48 kaynak nesnesi + core/kmod ile cross-build/link geçti.
Aynı 48 kaynak network-experiment define=1 ile ayrıca compile edildi; bu
experimental yolun loadable binary'si teslim edilmedi. MH_KEXT_BUNDLE,
PCI primary/secondary personality, kmod, private-symbol check ve public XNU
export audit yapıldı. Native High Sierra family exports/ABI tekrar -n -t ister.

Ring helper 64/128 ringlerde 20.480 geçerli from/to çiftinin mesafesini
bağımsız adım sayarak karşılaştırır; 5 invalid input ve failure'da output'un
korunması da ASan/UBSan altında geçti. TX runtime guard bu helper'ı kullanır.
Host PCI 7 case, core 92 assertion ve 5.000 malformed frame girdisi geçti.
0.2.2'de geçen crypto 220 ve bounded-search 10 testi değişmeyen math koduna
aittir; bu turda bu iki suite gereksiz tekrar çalıştırılmadı.

RX DMA replacement/IRQ runtime Mac'te test edilmedi. Compiler-preprocessed
PCI-only start audit donanım çağrılarını içermez; runtime superclass/ABI
güvenliğini kanıtlamaz. Default binary firmware/radio/IRQ/DMA'yı başlatmaz.

## Neden henüz ağ binary'si değil?

PCI-only gerçek attach çıktısı hâlâ verilmedi; son kullanıcı kextstat çıktısı
0.2.1 ve boş driver node idi. Windows kart bilgileri tamamdır; yeni Windows
bilgisi gerekmiyor. macOS'taki gerçek attach ayrı bir ölçümdür.

Ayrıca IODMACommand header'ı autoPrepare çağrılarının gated context'te
blocking riskini açıkça belirtir. Portun RX/TX mapping çağrıları hâlâ gated
network actions içinde; blocking mapping'i gate dışına taşıyan preprepared
buffer/worker düzeni tamamlanmadan bu yol kullanıma hazır değildir. Yeni RX
transaction bu threading sorununu çözdüğü iddiasında değildir. Fiziksel
PCI/firmware/RF/scan/WPA2/DHCP ve bu lifecycle tasarımı ayrı doğrulanmalıdır.

Native Mac/Xcode burada yok; kullanıcıya ait karta erişim yok. 0.2.3 ZIP
PCI-only tanı kext'ini ve offline aracı içerir; çalışan internet sürücüsü
olarak sunulmaz. Default tanı test akışı NETWORK.md'dedir. Kaynaklar ve eski
0.2.1/0.2.2 arşivleri korunmuştur.
