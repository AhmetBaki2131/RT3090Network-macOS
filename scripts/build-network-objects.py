#!/usr/bin/env python3
"""Compile the Ralink backend and BSD Wi-Fi stack. Not a loadable driver build."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--compiler", required=True)
parser.add_argument("--network-experiment", action="store_true", help="Compile withheld hardware start path; never enable it via runtime properties")
parser.add_argument("--output-dir", type=Path)
parser.add_argument("--diagnostic", action="store_true")
args = parser.parse_args()
out = args.output_dir or root / "build/network"
out.mkdir(parents=True, exist_ok=True)
sources = [root / "port/rt2860.cpp", root / "port/RTBSDGlue.cpp", root / "port/RT3090Network.cpp", root / "port/rijndael.c", root / "port/RTTimeout.cpp", root / "port/ieee80211.c", root / "port/RTMbuf.cpp", root / "port/RTIfq.cpp", root / "port/RTConnection.cpp", root / "port/ieee80211_input.c", root / "port/ieee80211_pae_output.c", root / "port/ieee80211_node.c", root / "port/ieee80211_proto.c", root / "port/ieee80211_pae_input.c", root / "port/ieee80211_mira.c"]
for folder in ["net80211", "crypto", "sys"]:
    sources += sorted((root / "vendor/itl80211/openbsd" / folder).glob("*.c"))
    sources += sorted((root / "vendor/itl80211/openbsd" / folder).glob("*.cpp"))
sources = [source for source in sources if source != root/"vendor/itl80211/openbsd/sys/_task.cpp"
           and source != root/"vendor/itl80211/openbsd/crypto/rijndael.c"
           and source != root/"vendor/itl80211/openbsd/net80211/CTimeout.cpp"
           and source != root/"vendor/itl80211/openbsd/net80211/ieee80211.c"
           and source != root/"vendor/itl80211/openbsd/sys/_mbuf.cpp"
           and source != root/"vendor/itl80211/openbsd/sys/_ifq.cpp"
           and source != root/"vendor/itl80211/openbsd/net80211/ieee80211_input.c"
           and source != root/"vendor/itl80211/openbsd/net80211/ieee80211_pae_output.c"
           and source != root/"vendor/itl80211/openbsd/net80211/ieee80211_node.c"
           and source != root/"vendor/itl80211/openbsd/net80211/ieee80211_proto.c"
           and source != root/"vendor/itl80211/openbsd/net80211/ieee80211_pae_input.c"
           and source != root/"vendor/itl80211/openbsd/net80211/ieee80211_mira.c"]
flags = ["-target", "x86_64-apple-macosx10.13", "-x", "c++", "-std=gnu++14", "-mkernel",
         "-fapple-kext", "-fno-exceptions", "-fno-rtti", "-fno-stack-protector", "-nostdinc",
         "-fno-register-global-dtors-with-atexit", "-mllvm", "-disable-atexit-based-global-dtor-lowering",
         "-ffreestanding", "-fno-builtin", "-mno-red-zone", "-mno-sse", "-mno-sse2", "-mno-mmx",
         "-D_FORTIFY_SOURCE=0", "-DKERNEL", "-DKERNEL_PRIVATE", "-DDRIVER_PRIVATE", "-DIEEE80211_STA_ONLY", "-ferror-limit=0"]
for include in ["port", "include", "build/generated", "vendor/itl80211/openbsd", "vendor/itl80211", "vendor/itl80211/linux", "vendor/MacKernelSDK/Headers"]:
    flags += ["-I" + str(root / include)]
flags += ["-include", str(root / "port/RTBSDPrefix.hpp")]
if args.diagnostic:
    flags += ["-DRT3090_ENABLE_NETWORK_EXPERIMENT=0"]
if args.network_experiment:
    flags += ["-DRT3090_ENABLE_NETWORK_EXPERIMENT=1"]

def compile_one(source):
    stem = source.relative_to(root).as_posix().replace("/", "_")
    target = out / (stem + ".o")
    result = subprocess.run([args.compiler] + flags + ["-c", str(source), "-o", str(target)], capture_output=True, text=True)
    (out / (stem + ".log")).write_text(result.stdout + result.stderr)
    errors = [line for line in result.stderr.splitlines() if "error:" in line]
    return dict(source=source.relative_to(root).as_posix(), exit_code=result.returncode, errors=errors)

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(compile_one, sources))
(out / "compile-results.json").write_text(json.dumps(results, indent=2) + "\n")
failures = [item for item in results if item["exit_code"]]
print("Network object compilation:", len(results) - len(failures), "passed,", len(failures), "failed")
for item in failures:
    print(item["source"])
    for error in item["errors"][:4]:
        print(" ", error)
raise SystemExit(1 if failures else 0)
