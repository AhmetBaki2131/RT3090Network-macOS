# Lisans ve kaynak kayıtları

Yeni core adaptasyonu, kernel wrapper, testler ve scriptler
GPL-2.0-or-later altında sunulur. Linux'tan türeyen algoritmalar bu lisansı
korur. GPL-2.0 metni `licenses/GPL-2.0.txt` içinde; GPL v2 veya daha sonraki
sürüm seçimine ilişkin SPDX tanımları kaynakların üstündedir.

`vendor/linux/rt2x00` ve `eeprom_93cx6.c` değişmemiş kaynak snapshot'larıdır.
Orijinal copyright, author ve SPDX bildirimleri korunmuştur. Başlıca
rt2800 kaynaklarında Ivo van Doorn, Alban Browaeys, Felix Fietkau, Luis
Correia, Mattias Nissler, Mark Asselstine, Xose Vazquez Perez, Bart
Zolnierkiewicz ve ilgili kaynak dosyalarındaki diğer katkıcılar belirtilir.
EEPROM kaynağı rt2x00 SourceForge Project bildirimini korur. `crc-ccitt.c`
kendi mevcut copyright ve SPDX bildirimini korur. Her dosyanın lisansı
kendi bildirimi ile belirlenir; bu liste o bildirimlerin yerine geçmez.

`vendor/MacKernelSDK` acidanthera kaynak snapshot'ıdır. Kendi Apple/diğer
dosya bazlı lisansları, LICENSE.txt, header bildirimleri ve kmod kaynakları
değişmeden korunmuştur. Snapshot üçüncü taraf prebuilt `libkmod.a` da içerir;
bu RT3090 sürücü binary'si değildir. Yeni GPL kod için belirtilen lisans
Apple SDK başlıklarını otomatik olarak yeniden lisanslamaz.

`vendor/itl80211` itlwm'nin itl80211 dizininden alınmıştır. Net80211,
crypto ve sys kaynakları ağ hedefine entegredir. Orijinal dosya bazlı
ISC/BSD/GPL copyright ve lisansları korunmuştur; üst proje GPL lisansı
`licenses/itlwm-LICENSE` içindedir. `port/rijndael.c` aynı upstream AES
kaynağının adaptasyonudur; Td4 lookup tablosu signed-shift UB'sini önlemek
üzere uint32_t türüne çevrilmiştir, orijinal copyright korunur.

`vendor/openbsd` RT2860 kaynak snapshot'ı; `port/rt2860.cpp` ve
`port/dev/ic/rt2860*.h` onun türevleridir. Damien Bergamini ve diğer
katkıcıların dosya içindeki ISC izinleri aynen korunmuştur. Yeni GPL wrapper
bu dosyaların orijinal bildirimlerini kaldırmaz. Apple IONetworkingFamily,
VoodooWireless ve RalinkUtility yalnızca araştırma kaynaklarıdır.

Ralink firmware ayrı, açık kaynak olmayan bir binary'dir.
`firmware/rt2860.bin` orijinal 8192 byte dosyadır; deneme network kext'inde
değiştirilmeden embed edilir. `licenses/LICENCE.ralink-firmware.txt` değişmeden
korunmuştur. Lisans değiştirmeden binary dağıtımına koşullu izin verir;
ayrı patent izni OSI onaylı açık kaynak işletim sistemleriyle kombinasyona
sınırlıdır ve macOS kombinasyonunu kapsadığı iddia edilmez. Kaynakların GPL
lisansı veya bu paket bu kapsamı genişletmez. Varsayılan parametresiz build
firmware içermez; helper yalnızca verilen pinned dosyayı doğrular.

Commit kaynak kayıtları ve karşılaştırılabilir hash'ler `sources.json`
ve `docs/RESEARCH.md` içindedir. Paket hiçbir projeyle resmî ilişki veya
donanım üreticisinin desteğini iddia etmez.

0.2.2 yerel fork'ları port/RTTimeout.cpp ve port/ieee80211.c, vendor/itl80211
snapshot'ından türetilmiştir; allocation/error/lifecycle kontrolleri eklenmiştir.
Orijinal copyright/lisansları dosya başında korunur; vendor kopyaları değişmez.
