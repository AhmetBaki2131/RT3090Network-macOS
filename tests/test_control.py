# SPDX-License-Identifier: GPL-2.0-or-later
# Host-only tests: no CF/IOKit/macOS calls are made.
import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'tools/rt3090ctl.py'
spec=importlib.util.spec_from_file_location('control',p); control=importlib.util.module_from_spec(spec); spec.loader.exec_module(control)
assert control.interface_name({'IORegistryEntryChildren':[{'IORegistryEntryChildren':[{'BSD Name':'en7'}]}]})=='en7'
assert control.interface_name({'IORegistryEntryChildren':[]}) is None
assert control.utf8_bytes('Ağ')=='Ağ'.encode('utf-8')
assert control.as_bytes(b'abc')==b'abc'
control.snapshot=lambda:{'RT3090ControlledPortAuthorized':False,'IORegistryEntryChildren':[{'BSD Name':'en7'}]}
try: control.connectivity(False)
except RuntimeError as e: assert 'not authorized' in str(e)
else: raise AssertionError('Unauthorized Internet test accepted')
control.snapshot=lambda:{'RT3090ControlledPortAuthorized':True}
try: control.connectivity(False)
except RuntimeError as e: assert 'not found' in str(e)
else: raise AssertionError('Missing interface accepted')
print('PASS: interface selection, UTF-8 bytes and rejection of unauthorized/missing-interface connectivity tests; host fixtures only')
control.os.geteuid=lambda:0
control.snapshot=lambda:{'RT3090HardwareFailed':True}
try: control.request('join',b'network',b'password123')
except RuntimeError as e: assert 'fault' in str(e)
else: raise AssertionError('Faulted driver was automatically retried')
control.subprocess.check_output=lambda args:b''
# Restore the actual snapshot function after fixtures above.
actual_snapshot=spec.loader.get_code('control')
namespace={};exec(actual_snapshot,namespace)
try: namespace['snapshot']()
except RuntimeError as e: assert 'absent' in str(e)
else: raise AssertionError('Empty ioreg was accepted')
print('PASS: driver fault prevents automatic join retry; empty ioreg gets explicit error')
