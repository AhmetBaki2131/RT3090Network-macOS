#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile,re
r=Path(__file__).resolve().parent.parent;s=(r/'port/rt2860.cpp').read_text();a=s.index('\nrt2860_tx(')+1;b=s.index('{',a);e=s.index('\t/* pickup a rate index */',b);f='int\n'+s[a:e]+'return 0;}\n'
h='''
#include <cassert>
#include <cerrno>
#include <cstdint>
#define __mbuf packet
using u_int=unsigned;
#define nitems(a) (sizeof(a)/sizeof((a)[0]))
#define IOLog(...) ((void)0)
#define IEEE80211_S_RUN 4
#define IEEE80211_FC0_TYPE_MASK 12
#define IEEE80211_FC0_TYPE_MGT 0
#define IEEE80211_QOS_TID 15
#define EDCA_AC_BE 0
#define RT2860_TX_RING_COUNT 64
#define RT2860_TX_RING_ONEMORE 55
#define SLIST_FIRST(p) ((p)->head)
#define mtod(m,T) ((T)&(m)->wh)
struct ieee80211_frame {uint8_t i_fc[2];};
struct packet {unsigned len=64;ieee80211_frame wh{};};using mbuf_t=packet*;
struct ieee80211_node {};struct rt2860_node{};struct rt2860_tx_data{};struct rt2860_txd{};struct rt2860_txwi{};using bus_dma_segment_t=int;
struct rt2860_tx_ring {rt2860_txd *txd=nullptr;void *map=nullptr;unsigned cur=0,queued=0;void *data[64]{};};
struct ieee80211com {int ic_state=4;};
struct rt2860_softc {bool io_failed=false;ieee80211com sc_ic;struct {rt2860_tx_data *head;}data_pool;int mgtqid=5;rt2860_tx_ring txq[6];};
unsigned rt_run_tx_trace=0;
unsigned mbuf_pkthdr_len(packet *p){return p->len;}
int mbuf_pullup(packet**,unsigned){return 0;}
unsigned ieee80211_get_hdrlen(ieee80211_frame*){return 24;}
bool ieee80211_has_qos(ieee80211_frame*){return false;}
unsigned ieee80211_get_qos(ieee80211_frame*){return 0;}
unsigned ieee80211_up_to_ac(ieee80211com*,unsigned){return 0;}
'''
t='''
int main(){rt2860_softc sc;rt2860_tx_data data;sc.data_pool.head=&data;packet p;packet *m=&p;ieee80211_node ni;rt2860_txd desc;
 auto &ring=sc.txq[5];ring.txd=&desc;ring.map=&desc;
 assert(rt2860_tx(&sc,&m,&ni)==0);
 ring.cur=64;assert(rt2860_tx(&sc,&m,&ni)==EIO);ring.cur=0;
 ring.queued=56;assert(rt2860_tx(&sc,&m,&ni)==EIO);ring.queued=0;
 ring.data[0]=&data;assert(rt2860_tx(&sc,&m,&ni)==EIO);ring.data[0]=nullptr;
 ring.map=nullptr;assert(rt2860_tx(&sc,&m,&ni)==EIO);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real TX preflight: valid ring, out-of-range cursor, ring overflow, occupied slot, missing map; host only, rest of TX not executed.')
