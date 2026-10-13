#!/usr/bin/env python3
"""Clang source analysis, not PCI/race/ABI/hardware verification."""
from pathlib import Path
import argparse,subprocess,concurrent.futures,json
r=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--compiler',required=True);a=p.parse_args()
flags=['-target','x86_64-apple-macosx10.13','-x','c++','-std=gnu++14','-mkernel','-fapple-kext','-nostdinc','-fno-exceptions','-fno-rtti','-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DIEEE80211_STA_ONLY','-D_FORTIFY_SOURCE=0','-include',str(r/'port/RTBSDPrefix.hpp')]
for folder in ['port','include','build/generated','vendor/itl80211/openbsd','vendor/itl80211','vendor/itl80211/linux','vendor/MacKernelSDK/Headers']:flags+=['-I'+str(r/folder)]
files=['RT3090Network.cpp','RTBSDGlue.cpp','RTTimeout.cpp','RTMbuf.cpp','RTIfq.cpp','rt2860.cpp','RTConnection.cpp','ieee80211_pae_input.c','ieee80211_pae_output.c','ieee80211_input.c']
folder=r/'build/static-analysis';folder.mkdir(exist_ok=True)
def run(name):
 result=subprocess.run([a.compiler]+flags+['--analyze','-Xanalyzer','-analyzer-output=text',str(r/'port'/name)],capture_output=True,text=True)
 (folder/(name+'.log')).write_text(result.stdout+result.stderr)
 return {'source':name,'exit_code':result.returncode,'warnings':[line for line in result.stderr.splitlines() if 'warning:' in line]}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:reports=list(pool.map(run,files))
(folder/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports,indent=2));raise SystemExit(1 if any(item['exit_code'] for item in reports) else 0)
