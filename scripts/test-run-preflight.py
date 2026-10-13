#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent.parent
s=(r/'port/ieee80211_proto.c').read_text();a=s.index('    if (nstate == IEEE80211_S_RUN &&');b=s.index('\tostate = ic->ic_state;',a);guard=s[a:b]
h='''
#include <cassert>
#include <cerrno>
#define IEEE80211_S_RUN 4
#define IEEE80211_M_MONITOR 2
#define IOLog(...) ((void)0)
#define nitems(x) (sizeof(x)/sizeof((x)[0]))
struct ieee80211_node {struct {unsigned rs_nrates;unsigned char rs_rates[32];} ni_rates;unsigned ni_txrate;};
struct ieee80211com {int ic_opmode;ieee80211_node *ic_bss;};
'''
f='int preflight(ieee80211com *ic,int nstate){'+guard+'return 0;}'
t='''
int main(){ieee80211_node node{{4,{}},0};ieee80211com ic{1,&node};
 assert(preflight(&ic,4)==0);node.ni_rates.rs_nrates=0;assert(preflight(&ic,4)==EINVAL);
 node.ni_rates.rs_nrates=33;assert(preflight(&ic,4)==EINVAL);
 node.ni_rates.rs_nrates=4;node.ni_txrate=4;assert(preflight(&ic,4)==EINVAL);
 node.ni_txrate=3;assert(preflight(&ic,4)==0);
 ic.ic_bss=nullptr;assert(preflight(&ic,4)==EINVAL);
 assert(preflight(&ic,0)==0);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real net80211 RUN preflight: invalid rates/TX rate/BSS rejected before state mutation; valid RUN/INIT accepted; host only.')
