#!/usr/bin/env python3
"""Execute real HAL RUN transition using fault-injecting hardware/stack shims."""
from pathlib import Path
import subprocess,tempfile,re,sys,zipfile
r=Path(__file__).resolve().parent.parent
original='--original' in sys.argv
if original:
 s=(r/'tests/original/rt2860-newstate-0.3.2.cpp').read_text()
else: s=(r/'port/rt2860.cpp').read_text()
a=s.index('\nrt2860_newstate(')+1;b=s.index('{',a);depth=1;e=b+1
while depth: depth+=(s[e]=='{')-(s[e]=='}');e+=1
f='int\n'+s[a:e]
h=r'''
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstring>
#define IEEE80211_STA_ONLY 1
#define IOLog(...) ((void)0)
#define IEEE80211_IS_CHAN_2GHZ(c) true
#define IEEE80211_CHAN_ANYC ((ieee80211_channel*)-1)
#define IEEE80211_M_STA 1
#define IEEE80211_M_MONITOR 2
#define RT2860_LED_RADIO 1
#define RT2860_LED_LINK_2GHZ 2
#define RT2860_LED_LINK_5GHZ 4
#define RT2860_BCN_TIME_CFG 1
#define RT2860_BCN_TX_EN 1
#define RT2860_TSF_TIMER_EN 2
#define RT2860_TBTT_TIMER_EN 4
#define RT2860_INT_MASK 2
unsigned rt_run_tx_trace=0,rt_run_rx_trace=0;
enum ieee80211_state {IEEE80211_S_INIT,IEEE80211_S_SCAN,IEEE80211_S_AUTH,IEEE80211_S_ASSOC,IEEE80211_S_RUN};
struct ieee80211_channel {};
struct ieee80211_node { ieee80211_channel *ni_chan; struct { unsigned rs_nrates; } ni_rates; unsigned ni_txrate=0,ni_intval=100; uint8_t ni_bssid[6]{};bool ni_port_valid=false; };
struct rt2860_softc;
struct ieee80211com { struct {struct {void *if_softc;} ac_if;} ic_ac; ieee80211_state ic_state=IEEE80211_S_ASSOC; ieee80211_node *ic_bss; int ic_opmode=1; };
struct rt2860_softc {bool allow_join=true,io_failed=false;int (*sc_newstate)(ieee80211com*,ieee80211_state,int);};
bool dma_fault=false;const char *fail_stage=nullptr;int stack_calls=0,hardware_calls=0,masks=0;
bool rtbsd_dma_failed(){return dma_fault;}
void step(rt2860_softc *s,const char *name){++hardware_calls;if(fail_stage && !strcmp(name,fail_stage))s->io_failed=true;}
uint32_t RAL_READ(rt2860_softc*,int){return 0;}
void RAL_WRITE(rt2860_softc*,int reg,uint32_t v){if(reg==RT2860_INT_MASK && v==0)++masks;}
void rt2860_set_gp_timer(rt2860_softc *s,int){step(s,"timer");}
void rt2860_switch_chan(rt2860_softc *s,ieee80211_channel*){step(s,"channel");}
void rt2860_updateslot(ieee80211com *ic){step((rt2860_softc*)ic->ic_ac.ac_if.if_softc,"slot");}
void rt2860_enable_mrr(rt2860_softc *s){step(s,"rates");}
void rt2860_set_txpreamble(rt2860_softc *s){step(s,"preamble");}
void rt2860_set_basicrates(rt2860_softc *s){step(s,"basicrates");}
void rt2860_set_bssid(rt2860_softc *s,uint8_t*){step(s,"bssid");}
void rt2860_newassoc(ieee80211com *ic,ieee80211_node *ni,int){auto *s=(rt2860_softc*)ic->ic_ac.ac_if.if_softc;step(s,"assoc");if(!ni->ni_rates.rs_nrates)s->io_failed=true;}
void rt2860_enable_tsf_sync(rt2860_softc *s){step(s,"tsf");}
void rt2860_set_leds(rt2860_softc *s,int){step(s,"led");}
int stack(ieee80211com *ic,ieee80211_state state,int){++stack_calls;ic->ic_state=state;return 0;}
'''
t=r'''
int main(){
 ieee80211_channel ch;ieee80211_node node{&ch,{4}};rt2860_softc sc;sc.sc_newstate=stack;
 ieee80211com ic;ic.ic_ac.ac_if.if_softc=&sc;ic.ic_bss=&node;
 assert(rt2860_newstate(&ic,IEEE80211_S_RUN,-1)==0 && stack_calls==1 && ic.ic_state==IEEE80211_S_RUN);
 for(const char *name : {"timer","channel","slot","rates","preamble","basicrates","bssid","assoc","tsf","led"}) {
  sc.io_failed=false;sc.allow_join=true;ic.ic_state=IEEE80211_S_ASSOC;stack_calls=hardware_calls=0;fail_stage=name;
  assert(rt2860_newstate(&ic,IEEE80211_S_RUN,-1)==EIO);
  assert(stack_calls==0 && ic.ic_state==IEEE80211_S_ASSOC && !sc.allow_join);
 }
 fail_stage=nullptr;sc.io_failed=false;sc.allow_join=true;node.ni_rates.rs_nrates=0;stack_calls=0;
 assert(rt2860_newstate(&ic,IEEE80211_S_RUN,-1)==EIO && stack_calls==0);
 node.ni_rates.rs_nrates=4;sc.io_failed=false;sc.allow_join=true;ic.ic_bss=nullptr;
 assert(rt2860_newstate(&ic,IEEE80211_S_RUN,-1)==EINVAL);
 ic.ic_bss=&node;node.ni_chan=IEEE80211_CHAN_ANYC;
 assert(rt2860_newstate(&ic,IEEE80211_S_RUN,-1)==EINVAL);node.ni_chan=&ch;
 sc.sc_newstate=rt2860_newstate;
 assert(rt2860_newstate(&ic,IEEE80211_S_RUN,-1)==EINVAL);
 sc.sc_newstate=stack;dma_fault=true;
 assert(rt2860_newstate(&ic,IEEE80211_S_RUN,-1)==EIO);
}
'''
h=h.replace('#include <cstring>','#include <cstring>\n#include <initializer_list>')
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 result=subprocess.run([str(p/'test')],capture_output=True,text=True)
 if original:
  assert result.returncode != 0 and 'EIO' in result.stderr,result.stderr
  print('PASS negative control: 0.3.2 continued RUN despite injected stage fault')
  sys.exit(0)
 if result.returncode: print(result.stderr)
 assert result.returncode==0
print('PASS real HAL RUN transition: healthy path, 10 injected stage faults, empty rates, null BSS, recursive callback, DMA fault; ASan/UBSan host shims only.')
