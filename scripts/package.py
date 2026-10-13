#!/usr/bin/env python3
"""Package source/config/docs only, with reproducible order and SHA-256."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib

root = Path(__file__).resolve().parent.parent
output = root.parent / "RT3090-source.zip"
with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in {"build", ".git", "__pycache__", "xcuserdata"} for part in relative.parts):
            continue
        archive.write(path, str(Path("RT3090") / relative))
digest = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix(".zip.sha256").write_text(digest + "  " + output.name + "\n")
print(output, output.stat().st_size, "bytes")
print("SHA-256:", digest)

# Keep the earlier diagnostic distribution distinct from the network prototype.
bundle = root / "build/network/RT3090Network.kext"
if bundle.exists():
    import json
    from verify_kext import inspect
    report = inspect(bundle)
    validation = json.loads((root / "docs/network-validation.json").read_text())
    actual = hashlib.sha256((bundle / "Contents/MacOS/RT3090Network").read_bytes()).hexdigest()
    if actual != validation["binary_sha256"]:
        raise SystemExit("Network binary differs from the recorded validation; refusing stale packaging")
    network = root.parent / "RT3090Network-test.zip"
    prefix = Path("RT3090Network-test")
    with ZipFile(network, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                archive.write(path, str(prefix / "RT3090Network.kext" / path.relative_to(bundle)))
        for source, target in [
            ("tools/rt3090ctl.py", "rt3090ctl.py"), ("tools/rt3090-test.command", "rt3090-test.command"), ("README.md", "README.md"),
            ("docs/NETWORK.md", "NETWORK.md"), ("docs/network-validation.json", "network-validation.json"),
            ("THIRD_PARTY.md", "THIRD_PARTY.md"), ("sources.json", "sources.json"),
            ("build/network-link.log", "verification/network-link.log"),
            ("build/crypto-test.log", "verification/crypto-test.log"),
            ("build/core-test-final.log", "verification/core-test.log"),
            ("build/memchr-test.log", "verification/memchr-test.log"),
            ("build/high-sierra-import-audit.json", "verification/high-sierra-import-audit.json"),
            
            
            ("build/pci-test.log", "verification/pci-test.log"),
            ("build/diagnostic-start-audit.json", "verification/diagnostic-start-audit.json"),
            ("build/diagnostic-start.preprocessed.cpp", "verification/diagnostic-start.preprocessed.cpp"),
            ("build/ring-test.log", "verification/ring-test.log"),
            ("docs/NETWORK-0.3.0.md", "NETWORK-0.3.0.md"),
            ("build/dma-bridge-test.log", "verification/dma-bridge-test.log"),
            ("build/diagnostic-link.log", "verification/diagnostic-link.log"),
            ("tools/rt3090gui.py", "rt3090gui.py"),
            ("build/control-test.log", "verification/control-test.log"),
            ("build/app-structure.log", "verification/app-structure.log"),
            ("build/wpa-settings-test.log", "verification/wpa-settings-test.log"),
            ("docs/JOIN-FIX-0.3.1.md", "JOIN-FIX-0.3.1.md"),
            ("docs/FREEZE-FIX-0.3.2.md", "FREEZE-FIX-0.3.2.md"),
            ("docs/RUN-FIX-0.3.3.md", "RUN-FIX-0.3.3.md"),
            ("docs/AUDIT-0.3.4.md", "AUDIT-0.3.4.md"),
            ("docs/WPA2-0.3.4.md", "WPA2-0.3.4.md"),
            ("docs/BUG-AUDIT.md", "BUG-AUDIT.md"),
            ("docs/STABILITY-TESTS.md", "STABILITY-TESTS.md"),
            ("docs/NETWORK-TEST.md", "NETWORK-TEST.md"),
            ("build/connection-progress-test.log", "verification/connection-progress-test.log"),
            ("build/eapol-tx-state-test.log", "verification/eapol-tx-state-test.log"),
            ("build/wpa-status-path-test.log", "verification/wpa-status-path-test.log"),
            ("docs/RECOVERY.md", "RECOVERY.md"),
            ("build/bss-allocation-test.log", "verification/bss-allocation-test.log"),
            ("build/queue-ownership-test.log", "verification/queue-ownership-test.log"),
            ("build/send-ownership-test.log", "verification/send-ownership-test.log"),
            ("build/registry-status-test.log", "verification/registry-status-test.log"),
            ("build/manual-command-test.log", "verification/manual-command-test.log"),
            ("build/tx-preflight-test.log", "verification/tx-preflight-test.log"),
            ("build/proto-cleanup-test.log", "verification/proto-cleanup-test.log"),
            ("build/host-suite-0.3.4.log", "verification/host-suite-0.3.4.log"),
            ("build/run-transition-test.log", "verification/run-transition-test.log"),
            ("build/run-transition-negative-control.log", "verification/run-transition-negative-control.log"),
            ("build/run-preflight-test.log", "verification/run-preflight-test.log"),
            ("build/eapol-bounds-test.log", "verification/eapol-bounds-test.log"),
            ("build/key-validation-test.log", "verification/key-validation-test.log"),
            ("build/mcu-fault-test.log", "verification/mcu-fault-test.log"),
            ("build/host-suite-0.3.3.log", "verification/host-suite-0.3.3.log"),
            ("build/rx-ownership-test.log", "verification/rx-ownership-test.log"),
            ("build/node-timeout-test.log", "verification/node-timeout-test.log"),
            ("build/node-timeout-negative-control.log", "verification/node-timeout-negative-control.log"),
            ("build/timeout-lifecycle-test.log", "verification/timeout-lifecycle-test.log"),
            ("build/gui-request-test.log", "verification/gui-request-test.log"),
            ("build/hal-fault-test.log", "verification/hal-fault-test.log"),
            ("build/network-structure.json", "verification/network-structure.json"),
            ("build/diagnostic-structure.json", "verification/diagnostic-structure.json")]:
            archive.write(root / source, str(prefix / target))
        for folder, target in [(root / "build/diagnostic-release/RT3090Network.kext", prefix / "diagnostic/RT3090Network-Diagnostic.kext"), (root / "build/RT3090 Control.app", prefix / "RT3090 Control.app")]:
            for path in sorted(folder.rglob("*")):
                if path.is_file(): archive.write(path, str(target / path.relative_to(folder)))
        for path in sorted((root / "licenses").rglob("*")):
            if path.is_file(): archive.write(path, str(prefix / path.relative_to(root)))
        for path in sorted((root / "build/static-analysis").glob("*")):
            if path.is_file(): archive.write(path, str(prefix / "verification/static-analysis" / path.name))
        archive.writestr(str(prefix / "SOURCE.txt"), "Complete corresponding source: RT3090-source.zip, delivered alongside this archive.\nHardware validation and native macOS loading remain untested.\n")
    checksum = hashlib.sha256(network.read_bytes()).hexdigest()
    network.with_suffix(".zip.sha256").write_text(checksum + "  " + network.name + "\n")
    print(network, network.stat().st_size, "bytes")
    print("SHA-256:", checksum)
