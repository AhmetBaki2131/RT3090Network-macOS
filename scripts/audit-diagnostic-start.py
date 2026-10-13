#!/usr/bin/env python3
"""Inspect compiler-preprocessed start, not a runtime/hardware safety proof."""
from pathlib import Path
import argparse, subprocess, json
p=argparse.ArgumentParser(); p.add_argument('--compiler',required=True); a=p.parse_args()
r=Path(__file__).resolve().parent.parent
flags=['-target','x86_64-apple-macosx10.13','-x','c++','-std=gnu++14','-mkernel','-nostdinc','-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DIEEE80211_STA_ONLY','-D_FORTIFY_SOURCE=0']
for d in ['port','include','build/generated','vendor/itl80211/openbsd','vendor/itl80211','vendor/itl80211/linux','vendor/MacKernelSDK/Headers']: flags += ['-I'+str(r/d)]
flags += ['-include',str(r/'port/RTBSDPrefix.hpp')]
for mode in [0,1]:
    s=subprocess.check_output([a.compiler]+flags+['-DRT3090_ENABLE_NETWORK_EXPERIMENT='+str(mode),'-E','-P',str(r/'port/RT3090Network.cpp')],stderr=subprocess.DEVNULL,text=True)
    start=s.index('bool RT3090Network::start('); begin=s.index('{',start); depth=1; i=begin+1
    while depth:
        if s[i]=='{': depth+=1
        elif s[i]=='}': depth-=1
        i+=1
    body=s[start:i]; forbidden=['mapDeviceMemoryWithRegister','pci->open','setMemoryEnable','setBusMasterEnable','rt_read_eeprom','rt2860_attach','attachInterface','filterInterruptEventSource','timerEventSource']
    found=[x for x in forbidden if x in body]
    if mode==0:
        assert not found,found
        assert 'pci-diagnostic' in body and 'registerService()' in body
        (r/'build/diagnostic-start.preprocessed.cpp').write_text(body+'\n')
    else: assert 'rt2860_attach' in found and 'pci->open' in found
print(json.dumps(dict(diagnostic_start_hardware_calls=[],network_negative_control_detected=True,scope='compiler-preprocessed method only; superclass/ABI and real hardware untested'),indent=2))
