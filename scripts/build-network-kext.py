#!/usr/bin/env python3
"""Real cross-link of the unvalidated RT3090 network prototype."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from verify_kext import inspect

root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser()
p.add_argument("--compiler",required=True)
p.add_argument("--linker",required=True)
p.add_argument("--firmware",type=Path,default=root/"firmware/rt2860.bin")
p.add_argument("--diagnostic",action="store_true")
args=p.parse_args()
prepare=[sys.executable,str(root/"scripts/prepare_firmware.py"),"--output",str(root/"build/generated/FirmwareData.h")]
if args.firmware:
    prepare += ["--firmware",str(args.firmware)]
subprocess.check_call(prepare)
subprocess.check_call([sys.executable,str(root/"scripts/build-network-objects.py"),"--compiler",args.compiler]+(["--diagnostic"] if args.diagnostic else []))
folder=root/"build/network"
flags=["-target","x86_64-apple-macosx10.13","-mkernel","-nostdinc","-fno-stack-protector","-D_FORTIFY_SOURCE=0", "-DKERNEL","-DKERNEL_PRIVATE","-DDRIVER_PRIVATE",
       "-I"+str(root/"include"),"-I"+str(root/"vendor/MacKernelSDK/Headers")]
for source in ["src/rt3090_core.c","cross/NetworkKmodInfo.c"]:
    subprocess.check_call([args.compiler,"-x","c"]+flags+["-c",str(root/source),"-o",str(folder/(Path(source).stem+".o"))])
results=json.loads((folder/"compile-results.json").read_text())
objects=[folder/(item["source"].replace("/","_")+".o") for item in results]
objects += [folder/"rt3090_core.o",folder/"NetworkKmodInfo.o"]
bundle=folder/"RT3090Network.kext"
linker=[args.linker]
version_flags=["-macosx_version_min", "10.13"]
if Path(args.linker).name in {"ld.lld", "ld.lld.exe", "lld", "lld.exe"}:
    linker += ["-flavor", "darwin"]
    version_flags=["-platform_version", "macos", "10.13", "10.13"]
with tempfile.TemporaryDirectory(dir=folder) as staging:
    candidate=Path(staging)/"RT3090Network.kext"
    (candidate/"Contents/MacOS").mkdir(parents=True)
    shutil.copy2(root/"InfoNetwork.plist",candidate/"Contents/Info.plist")
    subprocess.check_call(linker+["-arch","x86_64"]+version_flags+["-kext","-undefined","dynamic_lookup"]+
                         [str(path) for path in objects]+[str(root/"vendor/MacKernelSDK/Library/x86_64/libkmod.a"),"-o",str(candidate/"Contents/MacOS/RT3090Network")])
    report=inspect(candidate)
    shutil.copytree(candidate,bundle,dirs_exist_ok=True)
    (folder/"network-structure.json").write_text(json.dumps(report,indent=2)+"\n")
print("Cross-linked prototype:",bundle)
print("Hardware scan/WPA2/DHCP untested. Native macOS kernel symbol validation still required.")
