#!/usr/bin/env python3
"""Run real node/mira timeout initializers with adjacent-memory canaries."""
from pathlib import Path
import subprocess,tempfile,sys,re
r=Path(__file__).resolve().parent.parent
original='--original' in sys.argv
base=r/('vendor/itl80211/openbsd/net80211' if original else 'port')
def function(name,file):
 s=(base/file).read_text(); a=s.index('\n'+name+'('); a=s.rfind('void',0,a); start=s.index('{',a); depth=1;b=start+1
 while depth:
  depth+=(s[b]=='{')-(s[b]=='}'); b+=1
 return s[a:b]
f=function('ieee80211_node_set_timeouts','ieee80211_node.c')
g=function('ieee80211_mira_node_init','ieee80211_mira.c')
callbacks=set(re.findall(r'timeout_set\([^,]+,\s*(\w+)',f+g))
h='''
#include <cassert>
#include <cstring>
#include <cstdlib>
#define IEEE80211_STA_ONLY 1
#define nitems(a) (sizeof(a)/sizeof((a)[0]))
#define EDCA_AC_BE 0
#define EDCA_AC_BK 1
#define EDCA_AC_VI 2
#define EDCA_AC_VO 3
#define IEEE80211_RTS_MAX 2347
#define IEEE80211_MIRA_PROBE_TO_UP 0
#define IEEE80211_MIRA_PROBE_TO_DOWN 1
struct CTimeout {};
struct ieee80211_node { CTimeout* ni_addba_req_to[16]; int ni_addba_req_intval[16]; unsigned guard; };
struct ieee80211_mira_node { int agglen,rts_threshold; CTimeout* probe_to[2]; unsigned guard; };
void timeout_set(CTimeout **p,void (*)(void*),void*) { *p=(CTimeout*)1; }
void ieee80211_mira_reset_goodput_stats(ieee80211_mira_node*) {}
void ieee80211_mira_reset_collision_stats(ieee80211_mira_node*) {}
'''
h+='\n'.join('void '+c+'(void*) {}' for c in callbacks)
t='''
int main() {
 auto *ni=new ieee80211_node{}; ni->guard=0x12345678;
 ieee80211_node_set_timeouts(ni);
 assert(ni->guard==0x12345678);
 for(int i=0;i<16;i++) assert(ni->ni_addba_req_intval[i]==1);
 for(int i=0;i<4;i++) assert(ni->ni_addba_req_to[i]!=nullptr);
 for(int i=4;i<16;i++) assert(ni->ni_addba_req_to[i]==nullptr);
 delete ni;
 auto *mn=new ieee80211_mira_node{};
 ieee80211_mira_node_init(mn);
 assert(mn->agglen==1 && mn->rts_threshold==2347);
 assert(mn->probe_to[0] && mn->probe_to[1]);
 delete mn;
}
'''
if '--mira-only' in sys.argv:
 a=t.index(' auto *ni='); b=t.index(' auto *mn='); t=t[:a]+t[b:]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+g+t)
 subprocess.run(['c++','-fsanitize=address,undefined','-g',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 result=subprocess.run([str(p/'test')],capture_output=True,text=True)
 if original:
  assert result.returncode != 0 and 'heap-buffer-overflow' in result.stderr,result.stderr
  print('PASS negative control: original initializer causes ASan heap-buffer-overflow (node or mira selected)')
 else:
  if result.returncode: print(result.stderr)
  assert result.returncode==0
  print('PASS real node/mira initializers: adjacent fields, timer slots, intervals; ASan/UBSan')
