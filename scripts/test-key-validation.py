#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile,re
r=Path(__file__).resolve().parent.parent
s=(r/'port/rt2860.cpp').read_text();a=s.index('\nrt2860_set_key(');b=s.index('    if (!k',a);e=s.index('    IOLog(',b);validation=s[b:e]
h=(r/'vendor/itl80211/openbsd/net80211/ieee80211_crypto.h').read_text();a=h.index('enum ieee80211_cipher {');e=h.index('};',a)+2;enum=h[a:e]
group=next(line for line in h.splitlines() if re.match(r'#define\s+IEEE80211_KEY_GROUP\b',line))
pre='''
#include <cassert>
#include <cerrno>
#include <cstdint>
struct ieee80211_node {};
struct rt2860_node:ieee80211_node {uint8_t wcid=1;};
struct rt2860_softc {bool io_failed=false;};
struct ieee80211_key {unsigned k_cipher,k_id=0,k_len=16,k_flags=0;uint8_t k_key[32];};
bool dma=false;bool rtbsd_dma_failed(){return dma;}
'''
f='int validate(rt2860_softc *sc,ieee80211_node *ni,ieee80211_key *k){'+validation+'return 0;}\n'
t='''
int main(){
 rt2860_softc sc;rt2860_node ni;ieee80211_key k;k.k_cipher=IEEE80211_CIPHER_CCMP;
 assert(validate(&sc,&ni,&k)==0);
 k.k_len=15;assert(validate(&sc,&ni,&k)==EINVAL);k.k_len=16;
 assert(validate(&sc,nullptr,&k)==EINVAL);
 ni.wcid=255;assert(validate(&sc,&ni,&k)==EINVAL);ni.wcid=1;
 k.k_flags=IEEE80211_KEY_GROUP;k.k_id=3;assert(validate(&sc,nullptr,&k)==0);
 k.k_id=4;assert(validate(&sc,nullptr,&k)==EINVAL);k.k_id=0;
 k.k_len=33;assert(validate(&sc,nullptr,&k)==EINVAL);
 k.k_len=32;k.k_cipher=IEEE80211_CIPHER_TKIP;assert(validate(&sc,nullptr,&k)==0);
 sc.io_failed=true;assert(validate(&sc,nullptr,&k)==EINVAL);sc.io_failed=false;
 dma=true;assert(validate(&sc,nullptr,&k)==EINVAL);
 assert(validate(&sc,nullptr,nullptr)==EINVAL);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(pre+enum+'\n'+group+'\n'+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real key preflight: valid CCMP/TKIP, invalid lengths/IDs/WCID/node, group nil-node, sticky I/O/DMA fault; no hardware key install.')
