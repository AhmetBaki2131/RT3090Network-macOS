# 0.3.4 — geçici test komutları

Klasörü Desktop/RT3090Network-test olarak açın. AUDIT-0.3.4.md bu sürümün düzeltmelerini ve test sınırlarını açıklar. App'in Status ekranı kext yüklü olduğu için bağlantı var saymaz. PCI kartı görünürken controller yoksa not-attached ve varsa son start hata aşamasını gösterir. Bu WPA2 başarısızlığı değildir.

## 1. Yüklemeden doğrulama

```bash
sudo /bin/bash "$HOME/Desktop/RT3090Network-test/rt3090-test.command" check
```

Betik temiz bir /private/tmp dizinine kopyalar, root:wheel/izinleri düzeltir, kextutil -n -t çalıştırır ve geçici kopyayı temizler. Kext yüklenmez. Doğrulama/policy/symbol hatasında durur; SIP değiştirilmez. Başarılı doğrulama sistemin donmayacağını kanıtlamaz.

## 2. Eski sürüm varsa

```bash
kextstat -b org.rt3090.network
```

Modül yüklüyse load betiği durur. Yalnızca normal çalışan sistemde açıkça boşaltmak için:

```bash
sudo /bin/bash "$HOME/Desktop/RT3090Network-test/rt3090-test.command" unload
```

Boşaltma hatasında zorlamayın. Önceden EFI/Easy Kext Pro ile kurulmuş kopyalar yeniden başlatmada geri yüklenebilir. Bu betik o dosyalara veya cache'e dokunmaz.

## 3. Geçici yükleme

Doğrulama ve önceki sürümün ayrılması tamamlandıysa:

```bash
sudo /bin/bash "$HOME/Desktop/RT3090Network-test/rt3090-test.command" load
```

Bu işlem doğrulamayı aynı temiz staging kopyasında tekrar yapar; ancak başarılıysa yükler. Daha önce kurduğunuz kext'i değiştirmez. Yüklü sürümü kextstat ile kontrol edin: 0.3.4 olmalı.

## 4. Status ve Scan

```bash
/usr/bin/python "$HOME/Desktop/RT3090Network-test/rt3090ctl.py" status
```

not-attached, eksik BSD interface veya HardwareFailed durumunda Connect/Scan gönderilmez. Hatalı donanım durumu kernel enable callback'inde otomatik temizlenmez; arka arkaya retry yapılmaz. Yeni controller instance/yeniden başlatma ayrı kontrollü kurtarma adımıdır.

Bağlı controller ve enN arayüzü varsa önce tarama:

```bash
sudo /usr/bin/python "$HOME/Desktop/RT3090Network-test/rt3090ctl.py" scan
```

Yaklaşık 10 saniye sonra Status'a tekrar bakın. Boş liste tarama başarısı değildir.

## 5. Kontrollü Connect aşaması

Önceki sürümlerde Connect tüm sistemi dondurdu. Bu yeni sürüm kartta doğrulanmadı. Tarama/Status kararlı olmadan ve native doğrulama tamamlanmadan Connect'e geçmeyin. Önce dosyaları kaydedin; app ve kernel kayıtlarını Terminal'den ayrı izleyin:

```bash
sudo /usr/bin/python -u "$HOME/Desktop/RT3090Network-test/rt3090gui.py" 2>&1 | tee "$HOME/Desktop/RT3090-app-0.3.4.log"
```

Ayrı Terminal:

```bash
sudo log stream --style syslog --predicate 'process == "kernel" AND eventMessage CONTAINS[c] "RT3090"' 2>&1 | tee "$HOME/Desktop/RT3090-kernel-0.3.4.log"
```

Bu pipeline'lar yalnızca görüntüleme/kayıt içindir; çıkışlarını yüklemeye koşul yapmayın. Tam donmada son kayıt diske yazılamayabilir. RUN alt-adım begin/complete, EAPOL ve key install izleri yazılır; complete fiziksel bağlantı kanıtı değildir.

GUI'de Connect; CLI tercih edilirse:

```bash
sudo /usr/bin/python "$HOME/Desktop/RT3090Network-test/rt3090ctl.py" connect "Aginin adi"
```

Şifre prompt'ta girilir; argv veya logda gösterilmez. Request accepted yalnızca kontrol isteğinin dönüşüdür. Association RUN (4), WPA2 el sıkışması ve Port authorized ayrı aşamalardır. Hata durumunda tekrar Connect göndermeyin.

## 6. IP ve trafik

Yalnızca Controlled port authorized=True sonrasında:

```bash
sudo /usr/bin/python "$HOME/Desktop/RT3090Network-test/rt3090ctl.py" dhcp
```

Birkaç saniye sonra:

```bash
/usr/bin/python "$HOME/Desktop/RT3090Network-test/rt3090ctl.py" check
```

Check enN için IP, doğru route, kaynak IP'ye bağlı ping/TLS ve sistem DNS'i kontrol eder. Ping bekleme sınırı vardır. DNS sistem resolver'ıdır; onun RT3090 üzerinden geçtiği ayrıca incelenir. TLS doğrulaması kapatılmaz. DHCP request submitted IP/internet kanıtı değildir.

## Geri alma

App'i kapatıp yukarıdaki unload komutunu çalıştırın. Bu sadece modülü boşaltır; kalıcı kurulmuş kopyayı kaldırmaz. Betik yalnızca kendi mktemp staging dizinini temizler. Tam kilitlenmede güç düğmesi son çaredir; veri kaybı olabilir. Yeniden açıldıktan sonra aynı Connect denemesini tekrarlamayın. Panic raporu yokluğu kernel donmasını dışlamaz.


## Ek trafik ve yeniden bağlanma kontrolü
Yetkilendirme ve DHCP başarılı olduktan sonra gateway ARP kaydı, TCP/UDP aktarımı ve paket kaybını ayrıca ölçün. Disconnect sonrası port False olmalı ve trafik durmalıdır; yeniden Connect için yeni handshake gözlenmelidir. Bu testler cloud ortamında yapılmadı. Donma tekrarlanırsa testi durdurun; başarılı bağlantı raporlamayın.
