#!/usr/bin/env python3
"""Package only a verified freshly built network kext; never use release archives."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from verify_kext import inspect

root = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser()
p.add_argument('--bundle', type=Path, required=True)
p.add_argument('--output', type=Path, default=root/'build/RT3090Network-0.3.5-test.zip')
args = p.parse_args()
report = inspect(args.bundle)
info = plistlib.loads((args.bundle/'Contents/Info.plist').read_bytes())
expected = plistlib.loads((root/'InfoNetwork.plist').read_bytes())
if info['CFBundleVersion'] != expected['CFBundleVersion']:
    raise SystemExit('Refusing a stale bundle version')
binary = args.bundle/'Contents/MacOS'/info['CFBundleExecutable']
report.update(version=info['CFBundleVersion'], binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
app = root/'build/RT3090 Control.app'
if not (app/'Contents/MacOS/RT3090Control').is_file():
    raise SystemExit('Run scripts/make-control-app.py first')
app_info = plistlib.loads((app/'Contents/Info.plist').read_bytes())
if app_info['CFBundleVersion'] != expected['CFBundleVersion']:
    raise SystemExit('Refusing stale control app version')
for name in ['rt3090ctl.py', 'rt3090gui.py']:
    if (app/'Contents/Resources'/name).read_bytes() != (root/'tools'/name).read_bytes():
        raise SystemExit('Refusing stale app resource: '+name)
args.output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=args.output.parent) as staging:
    candidate = Path(staging)/args.output.name
    with ZipFile(candidate, 'w', compression=ZIP_DEFLATED) as z:
        def add(path, relative):
            entry = ZipInfo('RT3090Network-test/'+relative)
            entry.create_system = 3
            executable = path.suffix in {'.command', '.py', '.sh'} or '/Contents/MacOS/' in path.as_posix()
            entry.external_attr = (0o100755 if executable else 0o100644) << 16
            entry.compress_type = ZIP_DEFLATED
            z.writestr(entry, path.read_bytes())
        for folder in [args.bundle, app, root/'licenses']:
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    add(path, folder.name+'/'+path.relative_to(folder).as_posix())
        for source, target in [('tools/rt3090ctl.py','rt3090ctl.py'),
                               ('tools/rt3090gui.py','rt3090gui.py'),
                               ('tools/rt3090-test.command','rt3090-test.command'),
                               ('docs/START-HERE-0.3.5.md','START-HERE.md'),
                               ('docs/MCU-FIX-0.3.5.md','MCU-FIX-0.3.5.md'),
                               ('docs/RECOVERY.md','RECOVERY.md'),
                               ('THIRD_PARTY.md','THIRD_PARTY.md'), ('sources.json','sources.json')]:
            add(root/source, target)
        z.writestr('RT3090Network-test/verification/structure.json', json.dumps(report, indent=2)+'\n')
    candidate.replace(args.output)
digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
args.output.with_suffix('.zip.sha256').write_text(digest+'  '+args.output.name+'\n')
print(args.output)
print('Structure/version checked; native ABI and physical Wi-Fi operation require separate testing.')
