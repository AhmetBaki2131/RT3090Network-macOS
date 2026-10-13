from pathlib import Path
import importlib.util,plistlib,struct
r=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('ctl',r/'tools/rt3090ctl.py');ctl=importlib.util.module_from_spec(spec);spec.loader.exec_module(ctl)
card={'vendor-id':struct.pack('<I',0x1814),'device-id':struct.pack('<I',0x3090),'RT3090LastStartError':'EEPROM parse','RT3090LastAttemptVersion':'0.3.4'}
queue=[b'',plistlib.dumps([{'IORegistryEntryChildren':[card]}])]
ctl.subprocess.check_output=lambda args:queue.pop(0)
state=ctl.snapshot();assert state['RT3090Attached'] is False and state['RT3090Mode']=='not-attached' and state['RT3090LastStartError']=='EEPROM parse'
ctl.snapshot=lambda:state;ctl.os.geteuid=lambda:0
try:ctl.request('join',b'network',b'password123')
except RuntimeError as exc:assert 'not attached' in str(exc)
else:raise AssertionError('Radio request allowed without attachment')
ctl.snapshot=lambda:{'RT3090Attached':True,'RT3090Mode':'network-experimental'}
try:ctl.request('scan')
except RuntimeError as exc:assert 'no published BSD' in str(exc)
else:raise AssertionError('Radio request accepted without BSD interface')
assert ctl._pci_id(struct.pack('<I',0x3090))==0x3090 and ctl._pci_id(b'\0') is None
try:ctl._records(plistlib.dumps({'unexpected':'dict'}))
except RuntimeError:pass
else:raise AssertionError('Invalid registry schema accepted')
print('PASS registry fallback: real XML decode, recursive PCI identity, attached=false stage, no radio on missing interface, malformed schema rejection; no macOS calls.')
