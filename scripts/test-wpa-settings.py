#!/usr/bin/env python3
"""Compile and execute the unmodified vendor parameter function on host structs.
This tests real net80211 return semantics; no association/handshake/hardware.
"""
from pathlib import Path
import re,subprocess
root=Path(__file__).resolve().parent.parent; vendor=root/'vendor/itl80211/openbsd/net80211'
s=(vendor/'ieee80211_ioctl.c').read_text(); a=s.index('int\nieee80211_ioctl_setwpaparms('); b=s.index('\nint\n',a+4); function=s[a:b]
macros=[]
for header in ['ieee80211_ioctl.h','ieee80211_var.h']:
    for line in (vendor/header).read_text().splitlines():
        if re.match(r'#define\s+IEEE80211_(?:WPA_PROTO_|WPA_AKM_|WPA_CIPHER_|PROTO_|C_RSN\b|F_RSNON\b)',line): macros.append(line)
crypto=(vendor/'ieee80211_crypto.h').read_text()
enums=[]
for name in ['ieee80211_cipher','ieee80211_akm']:
    a=crypto.index('enum '+name+' {'); b=crypto.index('};',a)+2; enums.append(crypto[a:b])
test='''
struct ieee80211com {unsigned ic_caps,ic_flags,ic_rsnprotos,ic_rsnakms,ic_rsnciphers; enum ieee80211_cipher ic_rsngroupcipher;};
struct ieee80211_wpaparams {int i_enabled,i_protos,i_akms,i_ciphers,i_groupcipher;};
'''+function+'''
int main(void) {
 struct ieee80211com ic={0};
 struct ieee80211_wpaparams p={1,IEEE80211_WPA_PROTO_WPA2,IEEE80211_WPA_AKM_PSK,IEEE80211_WPA_CIPHER_CCMP,IEEE80211_WPA_CIPHER_CCMP};
 assert(ieee80211_ioctl_setwpaparms(&ic,&p)==ENODEV);
 ic.ic_caps=IEEE80211_C_RSN;
 int result=ieee80211_ioctl_setwpaparms(&ic,&p);
 assert(result==ENETRESET);
 assert(ic.ic_flags&IEEE80211_F_RSNON);
 assert(ic.ic_rsnprotos==IEEE80211_PROTO_RSN);
 assert(ic.ic_rsnakms==IEEE80211_AKM_PSK);
 assert(ic.ic_rsnciphers==IEEE80211_CIPHER_CCMP);
 assert(ic.ic_rsngroupcipher==IEEE80211_CIPHER_CCMP);
 assert(IEEE80211_PROTO_RSN!=IEEE80211_WPA_PROTO_WPA2);
 p.i_enabled=0; assert(ieee80211_ioctl_setwpaparms(&ic,&p)==ENETRESET);
 assert(!(ic.ic_flags&IEEE80211_F_RSNON));
 puts("PASS: real vendor WPA2 parameter application returns ENETRESET; CCMP/PSK/protocol and disable semantics verified; no handshake tested");
}
'''
(root/'build/wpa-settings-host.c').write_text('#include <errno.h>\n#include <assert.h>\n#include <stdio.h>\n'+ '\n'.join(macros+enums)+'\n'+test)
subprocess.check_call(['cc','-std=c99','-Wall','-Wextra','-fsanitize=address,undefined',str(root/'build/wpa-settings-host.c'),'-o',str(root/'build/test_wpa_settings')])
subprocess.check_call([str(root/'build/test_wpa_settings')])
