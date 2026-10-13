#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent.parent
s=(r/'port/ieee80211_node.c').read_text();a=s.index('\nieee80211_node_lateattach(')+1;b=s.index('{',a);depth=1;e=b+1
while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
f='void\n'+s[a:e]
h='''
#include <cassert>
#include <cstddef>
#define IEEE80211_STA_ONLY 1
#define IOLog(...) ((void)0)
#define IEEE80211_CHAN_ANYC ((void*)1)
#define IEEE80211_TXPOWER_MAX 100
struct _ifnet{};struct ieee80211_node{void *ni_chan=nullptr;};
struct ieee80211com{ieee80211_node *ic_bss=nullptr;int ic_txpower=0;};
bool fail=true;ieee80211_node node;
ieee80211_node *ieee80211_alloc_node_helper(ieee80211com*){return fail?nullptr:&node;}
ieee80211_node *ieee80211_ref_node(ieee80211_node *p){return p;}
'''
t='''
int main(){ieee80211com ic;ieee80211_node_lateattach((_ifnet*)&ic);assert(!ic.ic_bss);
 fail=false;ieee80211_node_lateattach((_ifnet*)&ic);assert(ic.ic_bss==&node&&node.ni_chan==IEEE80211_CHAN_ANYC&&ic.ic_txpower==100);}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real BSS lateattach: allocation failure returns without panic/dereference; successful initial node; host only.')
