#!/usr/bin/env python3
"""Execute real RX bridge and dequeue implementation against consuming interfaces."""
from pathlib import Path
import subprocess, tempfile, sys
r=Path(__file__).resolve().parent.parent
s=(r/('vendor/itl80211/openbsd/sys/_mbuf.cpp' if '--original' in sys.argv else 'port/RTMbuf.cpp')).read_text()
f=s[s.index('static IOReturn _if_input'):s.index('\nint if_input')]
s=(r/'vendor/itl80211/openbsd/sys/_mbuf.h').read_text()
d=s[s.index('static inline mbuf_t\nml_dequeue'):s.index('static inline mbuf_t\nml_dechain')]
h='''
#include <cassert>
#include <cstdlib>
#define MBUF_LIST_FOREACH(l,m) for(m=(l)->ml_head;m;m=m->next)
#define panic(...) abort()
#define XYLog(...) ((void)0)
using IOReturn=int; struct OSObject {}; const int kIOReturnSuccess=0;
struct Packet { Packet *next; }; using mbuf_t=Packet*;
struct mbuf_list { Packet *ml_head,*ml_tail; unsigned ml_len; };
Packet *mbuf_nextpkt(Packet *p) { return p->next; }
void mbuf_setnextpkt(Packet *p, Packet *n) { p->next=n; }
void mbuf_freem(Packet *p) { free(p); }
struct IONetworkInterface {
 static const int kInputOptionQueuePacket=1;
 int seen=0, flushed=0; bool consume=false;
 void inputPacket(Packet *p,int,int) {
  assert(p->next==nullptr); ++seen;
  if(consume) free(p); else { p->next=nullptr; free(p); }
 }
 void flushInputQueue() { ++flushed; }
};
struct Stats { unsigned inputPackets=0; };
struct _ifnet { IONetworkInterface *iface; Stats *netStat; };
'''
t='''
int main() {
 for(int mode=0;mode<3;++mode) {
  IONetworkInterface iface; iface.consume=(mode==1); Stats stats;
  _ifnet net{mode==2?nullptr:&iface,&stats}; mbuf_list list{};
  for(int i=0;i<8;++i) {
   auto *p=(Packet*)calloc(1,sizeof(Packet));
   if(list.ml_tail) list.ml_tail->next=p; else list.ml_head=p;
   list.ml_tail=p; ++list.ml_len;
  }
  assert(_if_input(nullptr,&net,&list,nullptr,nullptr)==0);
  assert(!list.ml_head && !list.ml_tail && list.ml_len==0);
  assert(iface.seen==(mode==2?0:8));
  assert(iface.flushed==(mode==2?0:1));
  assert(stats.inputPackets==(mode==2?0u:8u));
 }
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td); (p/'test.cpp').write_text(h+d+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined','-g',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('RX ownership: 3 scenarios / 24 packets passed (ASan/UBSan). Hardware untested.')
