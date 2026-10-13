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
