# RT3090 0.3.1 kaynak incelemesi — RX ownership düzeltmesi

Connect sonrası donmanın kesin nedeni belirlenemedi. Mevcut analytics kaydı kernel backtrace içermiyor. Donanım, native High Sierra kextutil ve WPA2 handshake bu ortamda test edilmedi.

## Düzeltilen somut hata
vendor/itl80211/openbsd/sys/_mbuf.cpp içindeki _if_input, inputPacket çağrısından sonra mbuf_nextpkt okuyordu. IONetworkInterface::inputPacket paketin mülkiyetini alır, nextpkt bağlantısını değiştirebilir ve backing ifnet olmadığında paketi serbest bırakır. Ayrıca paket tesliminde nextpkt NULL olmalıdır. Çok paketli listede assert, paket kaybı veya use-after-free mümkündür.

port/RTMbuf.cpp lisans korunarak yerel fork olarak eklendi. ml_dequeue teslimden önce çalışır; teslim sonrası paket okunmaz. Arayüz yoksa paket serbest bırakılır, panic çağrılmaz. Cloud ve Xcode kaynak listeleri vendor karşılığını dışlar ve yerel fork'u derler. Vendor kaynak değiştirilmedi.

## Gerçek kontroller
- RX: gerçek düzeltme fonksiyonu ve mevcut ml_dequeue kodu host testinde çalıştırıldı; 3 senaryo, 24 paket; ASan/UBSan geçti.
- Eski fonksiyon aynı çok paketli testte nextpkt assertion nedeniyle başarısız oldu (negatif kontrol).
- 48 kaynak birimi derlendi, 0 hata; core ve kmod nesneleriyle x86_64 MH_KEXT_BUNDLE bağlandı.
- verify_kext yapı kontrolü geçti; bu native kextutil yerine geçmez.
- Gerçek DMA bridge host-shim testi geçti. Fiziksel DMA ve IRQ doğrulanmadı.
- WPA2 parametre uygulama testi geçti. Authentication, association, 4-way handshake doğrulanmadı.
- Linker Linux ortamında /System/Library/Frameworks dizininin yokluğu uyarısı verdi; bağlantı başarılı.

## Açık inceleme noktaları
Kanal tablosundaki sınırsız arama (rt2860_set_chan), zamanlayıcı yaşam döngüsü, IRQ/workloop yoğunluğu ve Connect sırasında durum geçişleri ayrıca incelenmeli. Bunlar bu değişiklikte çözüldü olarak raporlanmıyor. RT2860_RIDX_MAX dahil son indeksin geçerliliği dikkate alınmalı; yalnızca aramanın sonuna ulaşılması tek başına taşma kanıtı değildir.

## Kullanım sınırı
Bu paket inceleme çıktısıdır; kurulum paketi değildir. Mevcut yayın ZIP'leri ve standalone kext değiştirilmedi. İnceleme derlemesi build/network altında üretildi, sürüm metadatası 0.3.1 olarak kaldı. Yeni, donması giderilmiş bir sürüm olarak sunulmaz. Connect'i güvenli ilan etmek için yeterli kanıt yok.

EFI, OpenCore, ACPI, SIP ve kullanıcı bilgisayarındaki dosyalara dokunulmadı. Yeni EFI oluşturulmadı. Kontrol aracı değiştirilmedi.
