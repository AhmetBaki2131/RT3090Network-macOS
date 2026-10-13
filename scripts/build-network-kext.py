#!/usr/bin/env python3
"""Real cross-link of the unvalidated RT3090 network prototype."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser()
p.add_argument("--compiler",required=True)
p.add_argument("--linker",required=True)
p.add_argument("--firmware",type=Path,default=root/"firmware/rt2860.bin")
p.add_argument("--diagnostic",action="store_true")
args=p.parse_args()
prepare=["python3",str(root/"scripts/prepare_firmware.py"),"--output",str(root/"build/generated/FirmwareData.h")]
if args.firmware:
    prepare += ["--firmware",str(args.firmware)]
subprocess.check_call(prepare)
subprocess.check_call(["python3",str(root/"scripts/build-network-objects.py"),"--compiler",args.compiler]+(["--diagnostic"] if args.diagnostic else []))
folder=root/"build/network"
flags=["-target","x86_64-apple-macosx10.13","-mkernel","-nostdinc","-fno-stack-protector","-D_FORTIFY_SOURCE=0", "-DKERNEL","-DKERNEL_PRIVATE","-DDRIVER_PRIVATE",
       "-I"+str(root/"include"),"-I"+str(root/"vendor/MacKernelSDK/Headers")]
for source in ["src/rt3090_core.c","cross/NetworkKmodInfo.c"]:
    subprocess.check_call([args.compiler,"-x","c"]+flags+["-c",str(root/source),"-o",str(folder/(Path(source).stem+".o"))])
results=json.loads((folder/"compile-results.json").read_text())
objects=[folder/(item["source"].replace("/","_")+".o") for item in results]
objects += [folder/"rt3090_core.o",folder/"NetworkKmodInfo.o"]
bundle=folder/"RT3090Network.kext"
(bundle/"Contents/MacOS").mkdir(parents=True,exist_ok=True)
shutil.copy2(root/"InfoNetwork.plist",bundle/"Contents/Info.plist")
subprocess.check_call([args.linker,"-arch","x86_64","-macosx_version_min","10.13","-kext","-undefined","dynamic_lookup"]+
                     [str(path) for path in objects]+[str(root/"vendor/MacKernelSDK/Library/x86_64/libkmod.a"),"-o",str(bundle/"Contents/MacOS/RT3090Network")])
print("Cross-linked prototype:",bundle)
print("Hardware scan/WPA2/DHCP untested. Native macOS kernel symbol validation still required.")
