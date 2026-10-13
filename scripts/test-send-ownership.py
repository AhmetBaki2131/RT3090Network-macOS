#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent.parent
s=(r/'port/RT3090Network.cpp').read_text();a=s.index('IOReturn RT3090Network::sendPacket(');b=s.index('{',a);depth=1;e=b+1
while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
f=s[a:e]
h='''
#include <cassert>
#include <cstdlib>
using IOReturn=int;struct OSObject {};
struct packet{};using mbuf_t=packet*;int freed=0,started=0,queued=0;bool full=false,dma=false;
const int IEEE80211_S_RUN=4,IEEE80211_F_RSNON=1,LINK_STATE_UP=4,kIOReturnOutputDropped=1,kIOReturnOutputSuccess=0;
struct _ifnet {int if_link_state=4;};
struct RT3090Network:OSObject {bool running=true;
 struct {bool io_failed=false;struct {int ic_state=4,ic_flags=1;struct {_ifnet ac_if;}ic_ac;}sc_ic;}chip;
 static IOReturn sendPacket(OSObject*,void*,void*,void*,void*);
};
#define OSDynamicCast(T,p) static_cast<T*>(p)
bool rtbsd_dma_failed(){return dma;}
void mbuf_freem(packet *p){++freed;free(p);}
int if_enqueue(_ifnet*,packet *p){++queued;mbuf_freem(p);return full?-1:0;}
void rt2860_start(_ifnet*){++started;}
'''
t='''
int main(){RT3090Network s;
 auto make=[](){return (packet*)malloc(sizeof(packet));};
 full=true;assert(s.sendPacket(&s,make(),nullptr,nullptr,nullptr)==1);assert(freed==1&&started==0&&queued==1);
 full=false;assert(s.sendPacket(&s,make(),nullptr,nullptr,nullptr)==0);assert(freed==2&&started==1);
 s.chip.io_failed=true;assert(s.sendPacket(&s,make(),nullptr,nullptr,nullptr)==1);assert(freed==3&&queued==2);
 s.chip.io_failed=false;s.chip.sc_ic.ic_ac.ac_if.if_link_state=2;
 assert(s.sendPacket(&s,make(),nullptr,nullptr,nullptr)==1);assert(freed==4&&queued==2);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real output bridge: queue failure consumes packet once; success ownership; fault and unauthorized link refuse before enqueue; host only.')
