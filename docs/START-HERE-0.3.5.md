# RT3090Network 0.3.5 — başlangıç

Bu sürüm HP Pavilion dv6 üzerindeki RT3090 (1814:3090 / 103c:1453) ve macOS High Sierra 10.13.6 x86_64 içindir. Windows üzerinde kext yüklenemez. Xcode 9.4.1, MacOSX10.13.sdk ve kaynak araçları için Python 3 gerekir; kontrol uygulaması High Sierra'nın `/usr/bin/python` 2.7/Tk ortamını kullanır.

## Kaynaktan paket oluşturma

Terminal'de kaynak klasörüne girip çalıştırın:

```bash
sh scripts/build-test-package-macos.sh
```

Çıktı: `build/RT3090Network-0.3.5-test.zip`. Komut firmware SHA-256/CRC kontrolü, Xcode derlemesi, Mach-O kext yapısı ve sürüm kontrolü yapar; kontrol uygulamasını ve geçici test betiğini ekler. Sürücü yüklemez. Eksik SDK veya herhangi bir doğrulama hatasında durur. Eski 0.3.4 kext'i yeni sürüm diye kopyalamaz.

## High Sierra'da geçici test

Yeni ZIP'i Masaüstü'ne çıkarın; `RT3090Network-test` klasörü oluşur. Önce yalnızca doğrulama:

```bash
sudo /bin/bash "$HOME/Desktop/RT3090Network-test/rt3090-test.command" check
```

`check` başarısızsa yüklemeye geçmeyin. Modül zaten yüklüyse `load` durur; mevcut kurulumları otomatik değiştirmez. Gerekirse çalışan sistemde açıkça boşaltın:

```bash
sudo /bin/bash "$HOME/Desktop/RT3090Network-test/rt3090-test.command" unload
```

Sonra geçici yükleme ve gerçek controller durumu:

```bash
sudo /bin/bash "$HOME/Desktop/RT3090Network-test/rt3090-test.command" load
/usr/bin/python "$HOME/Desktop/RT3090Network-test/rt3090ctl.py" status
```

`RT3090DriverVersion` 0.3.5 olmalı. PCI görünmesine rağmen controller/interface yoksa veya HardwareFailed true ise Scan/Connect'e geçmeyin. Ayrı Terminal'de kayıtları izleyin:

```bash
sudo /bin/bash "$HOME/Desktop/RT3090Network-test/rt3090-test.command" log
```

Başlangıçta SLEEP yanıtı zaman aşımına uğrarsa `initial SLEEP unacknowledged; attempting bounded WAKEUP`, ardından başarı durumunda `initial MCU WAKEUP acknowledged` görülmeli. WAKEUP da başarısızsa sürücü durur; ardışık otomatik denemeler yapmaz.

Controller ve enN arayüzü mevcutsa tarama:

```bash
sudo /usr/bin/python "$HOME/Desktop/RT3090Network-test/rt3090ctl.py" scan
```

Status ve tarama kararlıysa `RT3090 Control.app` üzerinden bağlantı denenebilir. Önceki sürümlerde Connect tüm sistemi dondurdu; bu kartta 0.3.5 testi yapılmadı. DHCP ve Check yalnızca `ControlledPortAuthorized=True` sonrasında kullanılabilir. MCU uyandırma onayı internet bağlantısı kanıtı değildir.

Paket EFI/OpenCore/ACPI/SMBIOS/SIP veya kalıcı Extensions kurulumunu değiştirmez. Geri alma için `RECOVERY.md` kullanın. Önceden kalıcı kurulmuş kopyalar yeniden başlatmada geri yüklenebilir.
