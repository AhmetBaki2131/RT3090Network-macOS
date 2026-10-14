#!/usr/bin/env python3
"""Build a script-based High Sierra app wrapper; native GUI runtime remains untested."""
from pathlib import Path
import plistlib,shutil
root=Path(__file__).resolve().parent.parent
app=root/'build/RT3090 Control.app'; resources=app/'Contents/Resources'; executable=app/'Contents/MacOS'
resources.mkdir(parents=True,exist_ok=True); executable.mkdir(parents=True,exist_ok=True)
for source in ['rt3090ctl.py','rt3090gui.py']: shutil.copy2(root/'tools'/source,resources/source)
(resources/'Launch.applescript').write_text('''on run argv
    set guiFile to item 1 of argv
    do shell script "/usr/bin/python " & quoted form of guiFile with administrator privileges
end run
''')
(executable/'RT3090Control').write_text('''#!/bin/sh
set -eu
app_resources=$(CDPATH= cd -- "$(dirname -- "$0")/../Resources" && pwd)
exec /usr/bin/osascript "$app_resources/Launch.applescript" "$app_resources/rt3090gui.py"
''')
(executable/'RT3090Control').chmod(0o755)
(app/'Contents/Info.plist').write_bytes(plistlib.dumps(dict(CFBundleName='RT3090 Control',CFBundleDisplayName='RT3090 Control',CFBundleIdentifier='org.rt3090.control',CFBundleExecutable='RT3090Control',CFBundlePackageType='APPL',CFBundleVersion='0.3.5',CFBundleShortVersionString='0.3.5',LSMinimumSystemVersion='10.13',NSHighResolutionCapable=True)))
print(app)
