# 0.3.5 — ilk SLEEP/WAKEUP sırası

## Kök neden ve değişiklik

README'deki son fiziksel gözlem `MCU completion timeout cmd=48` idi. 48 = 0x30 = SLEEP. Port, 20 ms sınırlı completion beklemesinden sonra `io_failed` işaretliyordu; init içindeki `SLEEP || WAKEUP` kısa devresi WAKEUP'ı atlıyordu. Pinned OpenBSD kaynağı (`vendor/openbsd/rt2860.c`) bu ilk SLEEP sonucunu önemsemeden WAKEUP gönderir. Bu davranış farkı `MCU-COMPARISON.md` içinde de kayıtlıydı.

Yeni `rt2860_mcu_init_wakeup` yalnızca başlangıçtaki SLEEP **completion timeout** sonucunu kurtarılabilir kabul eder. Status/CID temizlenir ve ardından bir kez WAKEUP gönderilir. WAKEUP doğru token/slot ve status=1 ile onaylanmadan RF başlatması devam etmez. Command-value token düzeni değiştirilmedi; token seçimindeki farkın fiziksel hatanın nedeni olduğu kanıtlanmadı.

Mailbox busy timeout, başarısız status, mevcut sticky fault, DMA/MMIO hatası ve WAKEUP timeout durdurucudur. Normal `rt2860_mcu_cmd` üzerinden gönderilen SLEEP dahil diğer komutların timeout davranışı değişmez. Hiçbir sticky fault temizlenmez. Bütün poll sınırları korunur; otomatik sonsuz retry yoktur.

Tek register MMIO okuma/yazma köprüsündeki geçersiz map/base/alignment/bounds durumları artık sessizce dönmek yerine DMA fault kaydeder. Yazma sonrası flush okumasının register aralığı da kontrol edilir. MCU kodu bu fault'u başlangıçta ve I/O sonrasında kontrol eder. Böylece bir bellek hatası SLEEP completion timeout toleransı altında gizlenmez. Timeout logları komut, token, CID ve status değerlerini içerir; ağ parolası/anahtar içermez.

## Derleme ve paketleme

Windows yol ayracı nedeniyle nesne dosyası adlarının bozulması giderildi; alt Python işlemleri aynı interpreter ile başlatılır. Cross build artık linker'in çıkış koduna güvenmekle yetinmez: geçici aday Mach-O üzerinde `verify_kext.inspect` başarılı olmadan sonucu yayımlamaz. Buradaki LLVM 23.1.3 LLD, `-kext` için uyarı verip MH_EXECUTE üretti; bu dosya reddedildi ve dağıtılmadı. Bu ortamda yüklenebilir yeni kext üretildiği iddia edilmez.

Native tek komutlu paket betiği yeni Xcode çıktısını, sürümünü ve kmod yapısını kontrol eder. 0.3.4 arşivlerinden binary almaz. Yeni test paketi sürümü 0.3.5'tir; eski sürüm arşivleri geçmiş kayıt olarak korunur.

## Doğrulama ve sınırlar

Gerçek MCU helper fonksiyonları host harness'ine çıkarılıp ASan/UBSan ile çalıştırıldı: dört completion slot'u, sağlıklı power sırası, yalnız SLEEP timeout -> başarılı WAKEUP, her iki komutta timeout, WAKEUP timeout, normal SLEEP timeout'unun fatal kalması, busy/status/MMIO/DMA/removed-card hataları ve önceden işaretli fault. MMIO/DMA köprüsünün gerçek kaynağı da host shim ile sınanır.

Tam test sonuçları teslimattaki `verification` klasöründedir. Host testleri ve 49 birimin Mach-O nesne derlemesi fiziksel kart, gerçek DMA/IRQ, High Sierra ABI veya WPA2/DHCP testi değildir. Önceki Connect donmasının kesin nedeni hâlâ fiziksel log/backtrace ile doğrulanmalıdır. Bu düzeltme bilinen başlatma regresyonunu hedefler; bütün sürücünün donanımda çalıştığı sonucu çıkarılmaz.
