#!/usr/bin/env python3
"""Execute real M2/M4 builders with allocation/queue failure injection."""
from pathlib import Path
import subprocess,tempfile,re
r=Path(__file__).resolve().parent.parent
s=(r/'port/ieee80211_pae_output.c').read_text()
def function(name):
 a=s.index('\n'+name+'(')+1;b=s.index('{',a);depth=1;e=b+1
 while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return 'int\n'+s[a:e]
f=function('ieee80211_send_4way_msg2')+function('ieee80211_send_4way_msg4')
rx=(r/'port/ieee80211_pae_input.c').read_text();a=rx.index('\nieee80211_recv_4way_msg1(')+1;b=rx.index('{',a);depth=1;e=b+1
while depth:depth+=(rx[e]=='{')-(rx[e]=='}');e+=1
f+='void\n'+rx[a:e]
h=(r/'vendor/itl80211/openbsd/net80211/ieee80211.h').read_text();a=h.index('struct ieee80211_eapol_key {');e=h.index('} __packed;',a)+len('} __packed;');key='\n'.join(line for line in h.splitlines() if re.match(r'#define\s+EAPOL_KEY_(NONCE|IV|MIC)_LEN\b',line))+'\n'+h[a:e]
pre='''
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include "RTConnection.hpp"
using u_int8_t=uint8_t;using u_int16_t=uint16_t;
#define __packed __attribute__((packed))
#define XYLog(...) ((void)0)
#define IOLog(...) ((void)0)
#define IFF_DEBUG 1
#define IEEE80211_STA_ONLY 1
#define DPRINTF(...) ((void)0)
#define RSNA_SUPP_INITIALIZE 0
#define IEEE80211_PMK_LEN 32
#define IEEE80211_NODE_PMK 1
#define IEEE80211_NODE_RSN_NEW_PTK 2
#define IEEE80211_ELEMID_VENDOR 221
#define IEEE80211_KDE_PMKID 4
static const uint8_t IEEE80211_OUI[]={0,15,172};
#define BE_READ_2(p) (((p)[0]<<8)|(p)[1])
#define RSNA_SUPP_PTKNEGOTIATING 2
#define RNSA_SUPP_PTKDONE 3
#define IEEE80211_PROTO_RSN 1
#define IEEE80211_PROTO_WPA 2
#define IEEE80211_WPAIE_MAXLEN 256
#define IEEE80211_RSNIE_MAXLEN 256
#define MBUF_DONTWAIT 0
#define MT_DATA 0
#define BE_WRITE_2(p,n) do{(p)[0]=(n)>>8;(p)[1]=(n);}while(0)
#define BE_WRITE_8(p,n) do{for(int i=0;i<8;i++)(p)[i]=uint64_t(n)>>(56-8*i);}while(0)
struct ieee80211_ptk {};
struct ieee80211_node {unsigned ni_rsn_supp_state=1,ni_rsnprotos=1,ni_rsncipher=8;uint64_t ni_replaycnt=0;ieee80211_ptk ni_ptk;bool ni_port_valid=false;unsigned ni_rsnakms=0,ni_flags=0;bool ni_replaycnt_ok=false;uint8_t ni_pmk[32]{},ni_nonce[32]{},ni_macaddr[6]{};};
struct ieee80211com {struct {unsigned if_flags=0;}ic_if;uint8_t ic_nonce[32]{},ic_psk[32]{},ic_myaddr[6]{};struct {unsigned is_rx_eapol_replay=0;}ic_stats;};
struct packet {uint8_t data[512]{};unsigned len=0;};using mbuf_t=packet*;
#define mtod(m,T) ((T)(m)->data)
bool oom=false;int queue_result=0;
packet *ieee80211_get_eapol_key(int,int,unsigned){return oom?nullptr:new packet;}
void mbuf_pkthdr_setlen(packet *p,unsigned n){p->len=n;}
void mbuf_setlen(packet *p,unsigned n){p->len=n;}
uint8_t *ieee80211_add_rsn(uint8_t *p,ieee80211com*,ieee80211_node*){return p+4;}
uint8_t *ieee80211_add_wpa(uint8_t *p,ieee80211com*,ieee80211_node*){return p+4;}
int ieee80211_cipher_keylen(unsigned){return 16;}
int ieee80211_send_eapol_key(ieee80211com*,packet *m,ieee80211_node *ni,const ieee80211_ptk*) {
 assert(ni->ni_rsn_supp_state==1||ni->ni_rsn_supp_state==2);
 assert(m->len>=95);delete m;return queue_result;
}
'''
pre+='\n'+r"""
uint64_t BE_READ_8(const uint8_t *p){uint64_t v=0;for(int i=0;i<8;i++)v=(v<<8)|p[i];return v;}
enum ieee80211_akm {MOCK_AKM=0};
struct ieee80211_pmk{uint8_t pmk_key[32];};
bool ieee80211_is_8021x_akm(ieee80211_akm){return false;}
ieee80211_pmk *ieee80211_pmksa_find(ieee80211com*,ieee80211_node*,const uint8_t*){return nullptr;}
void mock_random(void *p,size_t n){memset(p,1,n);}
#define arc4random_buf mock_random
void ieee80211_derive_ptk(ieee80211_akm,const uint8_t*,const uint8_t*,const uint8_t*,const uint8_t*,const uint8_t*,ieee80211_ptk *p){*p=ieee80211_ptk{};}
"""
t=''' 
int main(){rt_conn_reset();ieee80211com ic;ieee80211_node ni;uint8_t replay[8]{};ieee80211_ptk ptk;
 queue_result=ENOBUFS;assert(ieee80211_send_4way_msg2(&ic,&ni,replay,&ptk)==ENOBUFS&&ni.ni_rsn_supp_state==1&&rt_connection.txM2==0);
 queue_result=0;assert(ieee80211_send_4way_msg2(&ic,&ni,replay,&ptk)==0&&ni.ni_rsn_supp_state==2&&rt_connection.txM2==1);
 queue_result=ENOBUFS;assert(ieee80211_send_4way_msg4(&ic,&ni)==ENOBUFS&&ni.ni_rsn_supp_state==2&&rt_connection.txM4==0);
 queue_result=0;assert(ieee80211_send_4way_msg4(&ic,&ni)==0&&ni.ni_rsn_supp_state==3&&rt_connection.txM4==1&&!ni.ni_port_valid);
 ni.ni_rsn_supp_state=1;oom=true;assert(ieee80211_send_4way_msg2(&ic,&ni,replay,&ptk)==ENOMEM&&ni.ni_rsn_supp_state==1);
 ni.ni_rsn_supp_state=2;assert(ieee80211_send_4way_msg4(&ic,&ni)==ENOMEM&&ni.ni_rsn_supp_state==2);
 packet buf;auto *key=(ieee80211_eapol_key*)buf.data;oom=false;queue_result=0;
 rt_conn_reset();ni.ni_rsn_supp_state=0;ieee80211_recv_4way_msg1(&ic,key,&ni);
 assert(ni.ni_rsn_supp_state==0&&rt_connection.rxM1==1&&rt_connection.error==203&&rt_connection.txM2==0);
 rt_conn_reset();ni.ni_rsn_supp_state=1;ieee80211_recv_4way_msg1(&ic,key,&ni);
 assert(ni.ni_rsn_supp_state==2&&rt_connection.rxM1==1&&rt_connection.txM2==1);
 rt_conn_reset();ni.ni_rsn_supp_state=1;ni.ni_replaycnt_ok=true;ni.ni_replaycnt=10;BE_WRITE_8(key->replaycnt,9);
 ieee80211_recv_4way_msg1(&ic,key,&ni);assert(rt_connection.txM2==0&&ni.ni_rsn_supp_state==1&&ic.ic_stats.is_rx_eapol_replay==1);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(pre+key+'\n'+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined','-I'+str(r/'port'),str(p/'test.cpp'),str(r/'port/RTConnection.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS actual M1/M2/M4 functions: queue/OOM failure retains old supplicant state; success advances; counters accurate; port remains unauthorized. M1 INITIALIZE/replay rejection and valid M1->M2 verified. Crypto/send helpers mocked; no full handshake proof.')
