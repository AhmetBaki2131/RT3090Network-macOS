#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile,re
r=Path(__file__).resolve().parent.parent
h=(r/'vendor/itl80211/openbsd/net80211/ieee80211.h').read_text();a=h.index('struct ieee80211_eapol_key {');b=h.index('} __packed;',a)+len('} __packed;');key='\n'.join(line for line in h.splitlines() if re.match(r'#define\s+EAPOL_KEY_(NONCE|IV|MIC)_LEN\b',line))+'\n'+h[a:b]
s=(r/'port/ieee80211_pae_input.c').read_text();a=s.index('    bodylen = BE_READ_2(key->len);');b=s.index('    info = BE_READ_2(key->info);',a);check=s[a:b]
s=(r/'vendor/itl80211/openbsd/net80211/ieee80211_pae_input.c').read_text();a=s.index('    bodylen = BE_READ_2(key->len);');b=s.index('    info = BE_READ_2(key->info);',a);old=s[a:b]
pre='''
#include <cstdint>
#include <cassert>
#define __packed __attribute__((packed))
#define MCLBYTES 2048
using u_int8_t=uint8_t;
#define BE_READ_2(p) ((unsigned)((p)[0])<<8 | (p)[1])
struct packet {unsigned length;};
unsigned mbuf_pkthdr_len(packet *p){return p->length;}
'''
def fn(name,s):return 'bool '+name+'(ieee80211_eapol_key *key,packet *m){int bodylen,totlen,paylen;'+s+'return true;done:return false;}\n'
t='''
void set(uint8_t *p,unsigned n){p[0]=n>>8;p[1]=n;}
int main(){
 ieee80211_eapol_key key{};packet m{sizeof(key)};
 for(unsigned n=0;n<sizeof(key)-4;++n){set(key.len,n);assert(!fixed(&key,&m));}
 set(key.len,0);assert(original(&key,&m)); // original unsigned subtraction allowed malformed length
 set(key.len,sizeof(key)-4);assert(fixed(&key,&m));
 set(key.paylen,1);assert(!fixed(&key,&m));
 set(key.paylen,0);m.length=sizeof(key)-1;assert(!fixed(&key,&m));
 m.length=2048;set(key.len,2045);assert(!fixed(&key,&m));
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(pre+key+fn('fixed',check)+fn('original',old)+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real EAPOL struct/length checks: undersized declared body, key-data overflow, truncation, oversized body; original rejects too few; host only.')
