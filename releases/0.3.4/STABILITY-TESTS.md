# RT3090Network 0.3.4 — test sonuçları

core-test-final.log: PASS
crypto-test.log: PASS
dma-bridge-test.log: PASS
memchr-test.log: PASS
pci-test.log: PASS
ring-test.log: PASS
wpa-settings-test.log: PASS
control-test.log: PASS
rx-ownership-test.log: PASS
node-timeout-test.log: PASS
timeout-lifecycle-test.log: PASS
gui-request-test.log: PASS
hal-fault-test.log: PASS
run-transition-test.log: PASS
run-preflight-test.log: PASS
eapol-bounds-test.log: PASS
key-validation-test.log: PASS
mcu-fault-test.log: PASS
bss-allocation-test.log: PASS
queue-ownership-test.log: PASS
send-ownership-test.log: PASS
registry-status-test.log: PASS
manual-command-test.log: PASS
tx-preflight-test.log: PASS
proto-cleanup-test.log: PASS
connection-progress-test.log: PASS
eapol-tx-state-test.log: PASS
wpa-status-path-test.log: PASS
28 groups; hardware and native macOS tests unrun.


Normal ve PCI-only diagnostic hedefleri High Sierra x86_64 için çapraz derlendi. Ayrıntılar network-validation.json ve verification dizinindedir. ASan/UBSan host testlerinde shim/mock kullanılan donanım işlemleri fiziksel kart testi değildir. Statik analiz 10 kaynakta çalıştı; 18 dead-store uyarısı kaldı.

MacOSX10.13.sdk/Xcode 9.4.1 bu ortamda yok: native Xcode, kextutil, Python 2.7/Tk, IRQ/DMA donanımı, tam WPA2 handshake, DHCP, DNS ve internet testleri çalıştırılamadı. Yapı/import kontrolü native yükleme doğrulamasının yerini tutmaz.

GUI Scan/Connect/Disconnect/Status/DHCP/Check işlevleri içerir; bağlantı hızı telemetrisi henüz sunulmaz. Yükleme, PCI eşleşmesi, çalışma durumu ve yetkilendirme birbirinin başarı kanıtı değildir. Bu sürümün donmayı giderdiği fiziksel olarak doğrulanmadı.
