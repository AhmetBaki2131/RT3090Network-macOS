#!/usr/bin/env python3
"""Execute real interrupt/watchdog dispatch with injected faults; no real IRQ."""
from pathlib import Path
import tempfile,subprocess,re
r=Path(__file__).resolve().parent.parent
s=(r/'port/rt2860.cpp').read_text()
def extract(name,ret):
 a=s.index('\n'+name+'(')+1;b=s.index('{',a);depth=1;c=b+1
 while depth:
  depth+=(s[c]=='{')-(s[c]=='}');c+=1
 return ret+'\n'+s[a:c]
intr=extract('rt2860_intr','int');watch=extract('rt2860_watchdog','void');power=extract('b4inc','uint32_t')
constants=list(dict.fromkeys(re.findall(r'RT2860_[A-Z0-9_]+',intr)))
h='''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <initializer_list>
#define __predict_false(x) (x)
struct _ifnet {void *if_softc; int if_timer=0,if_oerrors=0;};
struct rt2860_softc { bool io_failed=false,fatal_dma_stop=false; int sc_tx_timer=0;
 struct {char dv_xname[8]="RT3090";} sc_dev;
};
uint32_t pending=0; int stopped=0,wd=0,rx=0,tx=0; bool fail_rx=false,dma=false;
uint32_t RAL_READ(rt2860_softc*,int){return pending;}
void RAL_WRITE(rt2860_softc*,int,uint32_t){}
bool rtbsd_dma_failed(){return dma;}
void rt2860_intr_coherent(rt2860_softc *sc){sc->io_failed=true;}
void rt2860_drain_stats_fifo(rt2860_softc*){}
void rt2860_tx_intr(rt2860_softc*,int){++tx;}
void rt2860_rx_intr(rt2860_softc *sc){++rx;if(fail_rx)sc->io_failed=true;}
void rt2860_tbtt_intr(rt2860_softc*){}
void rt2860_gp_intr(rt2860_softc*){}
void rt2860_stop(_ifnet*,int){++stopped;}
void ieee80211_watchdog(_ifnet*){++wd;}
'''
h+='\n'.join('#define '+c+' (1u<<'+str(i)+')' for i,c in enumerate(constants))
t='''
int main(){
 for (uint32_t input : {0u,0xffffffffu,0x12345678u}) {
  for(int delta=-15;delta<=15;++delta) {
   uint32_t expected=0;
   for(unsigned i=0;i<8;++i) {
    int value=int((input>>(i*4))&15)+delta;
    if(value<0)value=0;if(value>15)value=15;
    expected|=uint32_t(value)<<(i*4);
   }
   assert(b4inc(input,delta)==expected);
  }
 }
 rt2860_softc sc; pending=RT2860_RX_DONE_INT|RT2860_TX_DONE_INT0;
 fail_rx=true; assert(rt2860_intr(&sc)==1); assert(rx==1 && tx==0 && sc.io_failed);
 sc.io_failed=false;fail_rx=false;rx=tx=0;
 assert(rt2860_intr(&sc)==1);assert(rx==1 && tx==1 && !sc.io_failed);
 dma=true;rx=tx=0;rt2860_intr(&sc);assert(!rx&&!tx);dma=false;
 pending=0;assert(rt2860_intr(&sc)==0);
 _ifnet net;net.if_softc=&sc;sc.sc_tx_timer=1;
 rt2860_watchdog(&net);assert(sc.io_failed && stopped==1 && net.if_oerrors==1 && wd==0);
 sc.io_failed=false;sc.sc_tx_timer=3;rt2860_watchdog(&net);
 assert(sc.sc_tx_timer==2 && net.if_timer==1 && wd==1);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+'\n'+intr+watch+power+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real IRQ/watchdog dispatch: RX fault blocks subsequent TX; DMA fault, empty IRQ, TX timeout fail-stop, healthy watchdog; 93 power-word saturation cases; host only.')
