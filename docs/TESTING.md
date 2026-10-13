> Tarihsel aşama raporu. Güncel sürüm/komutlar README.md, NETWORK.md ve AUDIT-0.3.4.md içindedir; aşağıdaki eski yükleme komutlarını güncel pakete uygulamayın.

# Test ve hata ayıklama

> Bu belge önceki Diagnostic aşamasının kaydıdır. Yeni 0.2.0 ağ hedefinin
> güncel kod ve test durumu README.md, NETWORK.md ve network-validation.json içindedir.

## Donanımsız testler

```sh
sh scripts/test.sh
sh scripts/test.sh /path/to/rt2860.bin
```

Testler ASan/UBSan ile çalışır ve hatada nonzero exit verir. EEPROM için
93cx6 clock/command modeli, eFuse blok modeli, stuck-busy/removal durumları,
firmware window yazmaları, 32 bit DMA adres taşmaları, TXWI/RXWI, RSN
count/bounds kontrolleri ve 5.000 bozuk frame girdisi kullanılır.
Model gerçek RT3090 silikonunun yerini tutmaz; register erişimi/kernel
yarışları veya kart kalibrasyonu bu testlerden doğrulanamaz.

Gerçek firmware dosyasının length/CRC testi olmadan 87 assertion;
dosya verildiğinde 92 assertion yürür. WPA2-PSK/CCMP IE tanımak, WPA2 ağında
oturum açmakla aynı şey değildir.

## Fiziksel kart kimliği

Şu anda cihazda macOS yok. İleride Linux Live USB üzerinde:

```sh
lspci -nn -d 1814:
lspci -nnk -d 1814:
```

`1814:3090`, subsystem ID ve kullanılan Linux driver'ı kaydedin. MAC adresi
ve EEPROM dump'ı kişisel cihaz bilgisi içerir; herkese açık log'da gizleyin.
HP model adı, PCI/ASIC/RF tipi yerine geçmez.

## Gelecekteki High Sierra denemesi

Önce [RECOVERY.md](RECOVERY.md). Bu hedef yalnızca laboratuvar testidir.
Native build çıktısı veya teslim edilen cross-linked deneysel kext için,
`kextutil` dependency/ABI/signing hataları çözülmeden yüklemeye geçmeyin.
Cross-linked kext'i kullanıyorsanız ilk `ditto` komutunun kaynak yolunu
ZIP'ten çıkardığınız `RT3090Diagnostic.kext` diziniyle değiştirin.
High Sierra sürümünü kaydedin:

```sh
sw_vers
uname -a
```

1. Harici yedek boot/Recovery ve geri dönüş yolunu hazırlayın.
2. Kext'i EFI'ye veya `/System/Library/Extensions` altına koymayın.
3. Test kopyasını otomatik kext taranmayan bir staging dizinine koyun:

```sh
sudo mkdir -p /Library/RT3090Lab
sudo ditto build/DerivedData/Build/Products/Debug/RT3090Diagnostic.kext /Library/RT3090Lab/RT3090Diagnostic.kext
sudo chown -R root:wheel /Library/RT3090Lab/RT3090Diagnostic.kext
sudo chmod -R go-w /Library/RT3090Lab/RT3090Diagnostic.kext
sudo kextutil -n -t -v 6 /Library/RT3090Lab/RT3090Diagnostic.kext
```

`-n` validation'dır; yükleme başarısı olarak raporlanmaz. Bu build imzasızdır.
Production güvenlik politikasında reddedilmesi beklenebilir. Apple kext
imza yetkili sertifika veya özel geliştirme sistemi gerekir. Sıradan ad-hoc
codesign kernel yükleme izni sağlamaz. Signing/SIP hatalarını sembol/ABI
hatalarından ayrı teşhis edin; sistem Apple kext'lerini patch'lemeyin.

4. Bu sürücü varsayılan olarak **attach olmaz**. Yalnızca bir test boot'unda
   OpenCore/Clover menüsünden `-rt3090-lab` boot argümanı verin. Ana EFI'yi
   değiştirmeyin; kext'i bootloader'a enjekte etmeyin. Bootloader türü bu
   oturumda doğrulanmadığından XML/plist'e otomatik ekleme betiği yok.
5. Güvenlik politikasını ve validation'ı çözmüş test sistemi üzerinde
   manuel yükleyin:

```sh
sudo kextutil -v 6 /Library/RT3090Lab/RT3090Diagnostic.kext
kextstat -b org.rt3090.experimental
ioreg -r -c RT3090Diagnostic -l
log show --last 10m --style syslog --predicate 'eventMessage CONTAINS "RT3090"'
```

`kextstat` yalnızca module load kanıtıdır. IORegistry'deki ASIC, EEPROM,
RFType/MAC/chain değerlerinin Linux değerleriyle eşleşmesi gerekir.
`RT3090DMAMappingValidated=true` yalnızca test buffer mapping'ini gösterir;
cihazın DMA aktarımı yaptığını göstermez. DMA mapping başarısızlığı ayrıca
`RT3090DMAMappingResult` olarak kaydedilir. `RT3090WiFiImplemented=false`
bilinçli durumdur. Yeni ağ arayüzü beklemeyin.

6. EEPROM kanıtı alınmadan firmware deneyine geçmeyin. Firmware eklenmiş
   build için sonraki ayrı test boot'unda `-rt3090-lab -rt3090-fw` kullanın.
   `RT3090FirmwareBooted=true` yalnızca PBF ready gözlemi anlamına gelir;
   radyo, BBP init, scan veya association doğrulanmış değildir.

Sürücü başka bir driver tarafından aktif DMA/IRQ kullanıldığını gözlerse
başlatmayı reddeder. Bilinmeyen ASIC/bozuk EEPROM durumunda da reddeder.
Bu davranışı plist'i genişleterek veya return değerlerini başarılıya
çevirerek aşmayın.

## Tam sürücü için henüz çalıştırılmayan testler

Pasif gerçek beacon alımı, gerçek scan sonuçları, açık test ağında
association, WPA2-PSK/CCMP dört aşamalı handshake, yanlış parola/replay,
DHCP/ARP/DNS/HTTPS, trafik yükü, disconnect/rejoin, RF kill, sleep/wake,
tekrar load/unload ve panic regresyonları uygulanmış değildir.
İnternet testi için build/parser testini başarı kanıtı saymayın.
