#!/usr/bin/env python3
"""Compare every Mach-O import to Apple's pinned XNU public KPI exports.
Family-kext exports must be checked against installed High Sierra binaries.
"""
from pathlib import Path
import json
import sys
from verify_kext import inspect
root=Path(__file__).resolve().parent.parent
bundle=Path(sys.argv[1])
report=inspect(bundle)
public={}
for family in ['BSDKernel','IOKit','Libkern','Mach']:
    for arch in ['', '.x86_64']:
        for symbol in (root/'research/xnu-4570.71.2'/(family+arch+'.exports')).read_text().split():
            public[symbol]=family
imports=report['imported_symbols']
matched={s:public[s] for s in imports if s in public}
unmatched=[s for s in imports if s not in public]
private=set()
for family in ['Private','Unsupported']:
    for arch in ['', '.x86_64']:
        private.update((root/'research/xnu-4570.71.2'/(family+arch+'.exports')).read_text().split())
# IOPCIFamily and IONetworkingFamily are separate declared dependencies.
family_imports=[s for s in unmatched if any(c in s for c in ['IOPCIDevice','IONetworkController','IOEthernetController','IONetworkMedium','IOPacketQueue','IOEthernetInterface','IONetworkInterface'])]
unknown=[s for s in unmatched if s not in family_imports]
result=dict(xnu_tag='xnu-4570.71.2',imports_total=len(imports),public_xnu_matched=len(matched),public_xnu_imports=matched,
            family_kext_imports_requiring_native_validation=family_imports,unclassified_imports=unknown,
            private_only_imports=[s for s in unknown if s in private],
            limitation='Public export source comparison only; installed High Sierra family binaries and native kextutil remain required.')
print(json.dumps(result,indent=2))
if unknown: raise SystemExit(1)
