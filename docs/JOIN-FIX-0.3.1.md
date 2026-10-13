> Tarihsel aşama raporu. Güncel sürüm/komutlar README.md, NETWORK.md ve AUDIT-0.3.4.md içindedir; aşağıdaki eski yükleme komutlarını güncel pakete uygulamayın.

# 0.3.1 bağlantı isteği düzeltmesi

Kullanıcı 0.3.0'da gerçek AP taraması bildirdi: BSSID e0:19:54:b5:08:90,
kanal5, SSID Subfloor. Mode network-experimental, association1/SCAN,
supplicant0, port False, retry0, link2/DOWN; join 0xe00002bc döndü.
Bu physical scan kanıtı kullanıcıdan geldi; cloud testi olarak raporlanmaz.
WPA2 association/handshake veya internet başarısı henüz gözlenmedi.

## Kodda bulunan hata

ieee80211_ioctl_setwpaparms() destek varsa RSN/PSK/CCMP parametrelerini ve
RSNON flag'ini ayarlar, sonra ENETRESET döner. Bu normal uygulanmış-parametre
sonucudur; caller yeni state/reset akışını yürütmelidir. Önceki controller
nonzero dönüşlerin tamamını kIOReturnError kabul edip allow_join/scan öncesi
çıkıyordu. Yeni kod yalnızca 0 veya ENETRESET'i kabul eder; diğer hatalar
reddedilmeye devam eder ve loglanır. INIT zaten önce istenir, sonraki scan
association/handshake yolunu yeni parametrelerle başlatır.

Bu kaynak hatası kesin olarak bulunmuştur; yeni kart testinde başka bir
hatayla da karşılaşılabilir. Yanlış şifre olduğu iddia edilmedi.

## Raporlama düzeltmeleri

- Internal IEEE80211_PROTO_RSN=1 / WPA=2 ile ioctl WPA1=1/WPA2=2 sabitleri
  farklıdır. Scan label artık ni_supported_rsnprotos içindeki internal RSN/WPA
  bitlerini kullanır. Önceki WPA etiketi AP'nin gerçekten WPA1-only olduğunu
  kanıtlamaz. Cipher CCMP bitleri aynı internal cipher enum'dan okunur.
- LINK_STATE_DOWN=2, LINK_STATE_UP=4. Status isimle gösterir; eski yanlış
  sayısal yorum düzeltilir. Driver TX gate zaten doğru LINK_STATE_UP macro'sunu
  kullanıyordu; bu değişiklik veri güvenlik kontrolünü gevşetmez.
- Controller kendi IOEthernetInterface name prefix/unit değerlerini registry'ye
  aktarır; tool bu RT3090InterfaceName property'sini BSD child traversal'dan
  önce kullanır. Araç başka bir interface numarasını uydurmaz.
- GUI/CLI Python2.7 UTF-8 encoding header'ları eklendi, app resources yenilendi.
  Boş ioreg XML çıktısı artık açıklayıcı hata olur, XML parser generic hatası değil.

## Gerçek doğrulamalar

Normal ve diagnostic 48 C/C++ + core/kmod, gerçek ld64 ile cross-link geçti.
Yapı/kmod/import/PCI matching kontrolleri geçti. Unmodified vendor parameter
function minimal host types ile derlenip ASan/UBSan altında çalıştırıldı;
RSN/PSK/CCMP ayarları gerçekten uygulanırken ENETRESET döndüğü ve unsupported
capability için ENODEV döndüğü doğrulandı. Bu WPA2 four-way handshake testi
değildir. Python3 syntax ve controller host fixtures geçti; yeni GUI'nin
Python2.7/macOS çalıştırması cloud'da yapılmadı.

MacOSX10.13.sdk/Xcode9.4.1 native build ve 0.3.1 native kextutil henüz yok.
Kaynak 0.3.0 build/design sınırlamaları sürer: fiziksel DMA/coherency/IRQ,
WPA2 message1–4/key install/DHCP/DNS/TLS testleri yeni binary için gerekir.
EFI/OpenCore/ACPI/SIP/boot args değiştirilmedi; kalıcı kurulum yapılmaz.

## Yeni sürümü deneme

1. Network-test.zip'i açın; 0.3.1 ana kext'i -n -t ile native doğrulayın.
2. Eski module'ü kextunload ile kaldırın; busy/error varsa zorlamayın.
3. NETWORK.md'deki staging manuel yükleme akışıyla yeni dosyayı yükleyin.
4. kextstat version0.3.1 ve registry mode network-experimental doğrulayın.
5. GUI/CLI Connect sonra Status: association ve supplicant/port/link'i kaydedin.
   Join accepted başarılı internet bağlantısı değildir.
6. Port True ve Link up sonrası DHCP, birkaç saniye sonra Check.

Module değiştirilmeden sadece yeni .app kullanmak eski kernel join bug'ını
çözmez. Eski staging kopyasını yeniyle değiştirmeniz gerekir. NETWORK.md'de
load/rollback/panic recovery adımları bulunur; aynı iki kext birlikte yüklenmez.
