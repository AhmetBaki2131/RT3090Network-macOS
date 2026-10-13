#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent.parent
s=(r/'port/rt2860.cpp').read_text();a=s.index('\nrt2860_mcu_cmd(')+1;b=s.index('{',a);depth=1;e=b+1
while depth: depth+=(s[e]=='{')-(s[e]=='}');e+=1
f='int\n'+s[a:e]
h='''
#include <cassert>
#include <cerrno>
#include <cstdint>
#define IOLog(...) ((void)0)
#define DPRINTF(...) ((void)0)
#define RT2860_H2M_MAILBOX 1
#define RT2860_H2M_BUSY (1u<<24)
#define RT2860_TOKEN_NO_INTR 255
#define RT2860_H2M_MAILBOX_CID 2
#define RT2860_H2M_MAILBOX_STATUS 3
#define RT2860_HOST_CMD 4
struct rt2860_softc {bool io_failed=false;};
int mode=0,reads=0,writes=0,delays=0;
uint32_t RAL_READ(rt2860_softc*,int reg){++reads;
 if(reg==1)return mode==1?RT2860_H2M_BUSY:0;
 if(reg==2)return mode==2?0:7;
 if(reg==3)return mode==3?0:1;
 return 0;}
void RAL_WRITE(rt2860_softc*,int,uint32_t){++writes;}
void RAL_BARRIER_WRITE(rt2860_softc*){}
void DELAY(int){++delays;}
'''
t='''
int main(){rt2860_softc sc;
 assert(rt2860_mcu_cmd(&sc,7,0,1)==0 && !sc.io_failed);
 mode=1;reads=writes=delays=0;
 assert(rt2860_mcu_cmd(&sc,7,0,1)==EIO && sc.io_failed && reads==100 && writes==0);
 sc.io_failed=false;mode=2;reads=writes=delays=0;
 assert(rt2860_mcu_cmd(&sc,7,0,1)==ETIMEDOUT && sc.io_failed && reads==201);
 sc.io_failed=false;mode=3;assert(rt2860_mcu_cmd(&sc,7,0,1)==EIO && sc.io_failed);
 int old=reads;assert(rt2860_mcu_cmd(&sc,7,0,0)==EIO && reads==old);
 sc.io_failed=false;mode=0;assert(rt2860_mcu_cmd(&sc,7,0,0)==0);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real MCU command: bounded busy/completion timeouts, failed status, sticky fault rejection, healthy wait/no-wait; host only.')
