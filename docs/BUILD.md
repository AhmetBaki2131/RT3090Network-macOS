> Tarihsel aşama raporu. Güncel sürüm/komutlar README.md, NETWORK.md ve AUDIT-0.3.4.md içindedir; aşağıdaki eski yükleme komutlarını güncel pakete uygulamayın.

# Derleme

> Bu belge önceki Diagnostic aşamasının kaydıdır. Yeni 0.2.0 ağ hedefinin
> güncel kod ve test durumu README.md, NETWORK.md ve network-validation.json içindedir.

## Bu oturumdaki sonuç

Linux ortamında GCC ile core test executable'ı, Zig 0.13.0'un Clang frontend'i
ile C ve IOKit C++ kaynaklarının x86_64 Mach-O object'leri üretildi.
Firmware include açık ve kapalı biçimleri ayrı ayrı derlendi.
Xcode proje syntax/referansları kontrol edildi; native Xcode build çalışmadı.
Sonraki üretim aşamasında Apple ld64'ün Linux portu ile **gerçek x86_64
MH_KEXT_BUNDLE** bağlandı. `RT3090Diagnostic-kext.zip` deneysel, imzasız,
firmware içermeyen binary'yi ve yapısal doğrulama kaydını içerir.
macOS kernel symbol resolution, kext yükleme ve cihaz testleri yapılmadı.

## Mac/Xcode yolu

Tam Xcode, x86_64 compiler/linker ve Python 3 kullanın. High Sierra için
Xcode 9.4.1 (10.13.2+) uygun bir başlangıçtır. Güncel Python sürümlerinin
High Sierra desteği varsayılmamalı; uyumlu Python 3 kurulumu gerekir.

Önce seçilmiş Developer Directory ve SDK'yı kontrol edin:

```sh
xcode-select -p
xcodebuild -version
xcodebuild -showsdks
```

Birden fazla Xcode varsa yalnızca komut için `DEVELOPER_DIR` seçilebilir:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer sh scripts/build-macos.sh
```

`vendor/MacKernelSDK` header ve libkmod snapshot'ı bundle içinde bulunur;
yeniden download gerekmez. Pinned commit `sources.json` içindedir.
Bu, Apple'ın High Sierra userland SDK'sı veya tam Xcode dağıtımı değildir.
Deployment 10.13 için kullanılan Apple SDK kurulmuş Xcode'dan seçilir.

Xcode projesini doğrudan açmak da mümkündür. **RT3090Diagnostic** shared
scheme'i seçin. Target `com.apple.product-type.kernel-extension` olduğundan
Xcode kmod metadata/entry-point üretimini yapmalıdır; bu native adım bu
ortamda doğrulanamadı. Build hatalarını tam build log'u ile çözmek gerekir.

İsteğe bağlı firmware:

```sh
sh scripts/build-macos.sh /path/to/rt2860.bin
```

Helper yalnızca incelenmiş SHA-256 ve Linux CRC'sine uyan 8192 bayt dosyayı
kabul eder. Firmware binary'sini otomatik indirmez. Lisans içeriği
`licenses/LICENCE.ralink-firmware.txt` içindedir. Lisansın kullanım ve
patent kapsamını değerlendirmeden binary eklemeyin. Firmware dosyası
olmayan build varsayılan olarak EEPROM bring-up yapar.

## Linux'ta nesne derlemesini tekrarlamak

Zig 0.13.0 kullanın. Bu çalışmada araç pip'ten ayrı araştırma dizinine
kuruldu; arşivde Zig executable'ı yok.

```sh
python3 -m pip install --no-deps --target build/tools ziglang==0.13.0
ZIG="$PWD/build/tools/ziglang/zig" sh scripts/check-cross.sh
```

Bu komutlar `build/cross/*.o` üretir. MacKernelSDK'ya karşı nesne derleme
Apple kernel symbol resolution, signing, kernel ABI veya kext yükleme testi
değildir. `.o` dosyasını `.kext` diye yeniden adlandırmayın.

Xcode proje üreticisi:

```sh
python3 scripts/make_xcode_project.py
```

Üretici deterministic'tir; `.pbxproj` ve shared scheme zaten ZIP'te bulunur.
Sadece projeyi değiştirdiğinizde yeniden üretin. Başlık üretimi `build/`
altındadır; gerçek kernel header'ları ve Linux snapshot'ları değiştirilmez.

## Linux üzerinde gerçek kext cross-link

LLD 19, `-kext` seçeneğini tanıyormuş gibi warning vererek ignore ediyor
ve executable üretiyor. Bu yanlış format teslim edilmedi. Zig'in kendi
Mach-O linker'ı da `-kext` desteklemiyor. Bu nedenle gerçek Apple ld64
portu kullanıldı:

- Repo: https://github.com/tpoechtrager/cctools-port
- Branch: `921-ld64-409.12`
- Commit: `490466d7e5adb50006948d753400e2023dbc323d`
- Host compiler: Debian Clang 19.1.7; target compiler: Zig 0.13.0 / Clang.
- Configure: `--target=x86_64-apple-darwin17 --disable-tapi-support
  --disable-lto-support --disable-xar-support`; ardından `make -C ld64 -j3`.

Tam cctools build'inde eski `otool` hedefi modern Clang'ın tentative
definition davranışı nedeniyle bağlanamadı. Gerekli ld64 hedefi bağımsız
olarak başarıyla derlendi; otool'a veya TAPI/userland SDK stub'larına
bu kext bağlamasında ihtiyaç yok.

Araçlar hazırlanmışken kaynak kökünde:

```sh
ZIG=/path/to/zig LD64=/path/to/cctools/ld64/src/ld/ld sh scripts/build-cross-kext.sh
```

Script core/wrapper'ı yeniden derler, `cross/KmodInfo.c` ile kmod metadata
ekler, MacKernelSDK'nın `libkmod.a` dosyasını bağlar ve gerçek kext biçimini
kontrol eder. Bu metadata dosyası Xcode hedefinde yoktur; Xcode kendi
metadata'sını üretir.

Kernel derleme bayrakları freestanding, red-zone/SIMD kapalı ve Apple
kext ABI'si açık olacak biçimdedir. LLVM'nin Mach-O global destructor
lowering'i varsayılan olarak `__cxa_atexit` eklediğinden
`-mllvm -disable-atexit-based-global-dtor-lowering` kullanılır. Böylece
`__mod_init_func` ve `__mod_term_func` kernel bölümleri korunur. Validator
userland atexit/exception imports'u ve yanlış Mach-O türünü reddeder;
kontrolü atlayarak binary paketlemeyin.

Bağlayıcıdaki `/System/Library/Frameworks` bulunamadı warning'i default
arama dizininden kaynaklanır; komut userland framework/dylib bağlamaz.
298 kernel import'u yapı kaydında görünür; bunların çalışan High Sierra
kernel/KPI tarafından çözülmesi bu ortamda doğrulanamaz.
