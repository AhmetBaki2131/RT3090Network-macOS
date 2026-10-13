# RT3090Network geri alma

Güncel geçici doğrulama/yükleme/kaldırma komutları NETWORK.md içindedir. Test betiği EFI, Extensions, boot argümanları, SIP ve cache'i değiştirmez; yalnızca kendi geçici staging dizinini temizler.

Yüklü modülü boşaltmak için:

```bash
sudo kextunload -b org.rt3090.network
kextstat -b org.rt3090.network
```

Busy/error varsa zorlamayın. Bu komut diskten kaldırma değildir. Daha önce Easy Kext Pro veya EFI ile kurulmuş kopyanın nerede olduğu varsayılmaz; o kurulum ayrıca incelenmelidir. Rastgele Extensions klasörü veya Apple kext'leri silinmez.

Tam donma halinde güç düğmesi son çaredir; kaydedilmemiş veri kaybolabilir. Sonraki açılışta Connect'i tekrar denemeyin. Geçici test betiği otomatik yeniden yükleme yapmaz, fakat önceden kalıcı kurulmuş kopya yeniden yüklenebilir. Açılış başarısızsa daha önce çalışan kurtarma ortamını kullanın; bu proje yeni EFI üretmez veya mevcut EFI'yi düzenlemez.

Panic raporları /Library/Logs/DiagnosticReports altında bulunabilir; rapor olmaması donmayı dışlamaz. Kernel logundaki son RUN/TX/RX/EAPOL aşamasını koruyun. Donmanın giderildiği bu paket için fiziksel olarak doğrulanmadı.
