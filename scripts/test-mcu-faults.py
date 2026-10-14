#!/usr/bin/env python3
from pathlib import Path
import os,subprocess,tempfile
r=Path(__file__).resolve().parent.parent
s=(r/'port/rt2860.cpp').read_text()
def extract(name):
 a=s.index('\n'+name+'(')+1;b=s.index('{',a);depth=1;e=b+1
 while depth: depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return 'int\n'+s[a:e]+'\n'
f=''.join(extract(name) for name in ['rt2860_mcu_cmd_impl','rt2860_mcu_cmd','rt2860_mcu_init_wakeup'])
h='''
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <vector>
#define IOLog(...) ((void)0)
#define DPRINTF(...) ((void)0)
#define RT2860_H2M_MAILBOX 1
#define RT2860_H2M_BUSY (1u<<24)
#define RT2860_TOKEN_NO_INTR 255
#define RT2860_H2M_MAILBOX_CID 2
#define RT2860_H2M_MAILBOX_STATUS 3
#define RT2860_HOST_CMD 4
#define RT2860_MCU_CMD_SLEEP 0x30
#define RT2860_MCU_CMD_WAKEUP 0x31
struct rt2860_softc {bool io_failed=false;};
int mode=0,reads=0,writes=0,delays=0,current=7,slot=0;
bool dma=false;
std::vector<uint32_t> commands,mailboxes,clears;
bool rtbsd_dma_failed(){return dma;}
uint32_t RAL_READ(rt2860_softc*,int reg){++reads;
 if(reg==1)return mode==9?0xffffffffu:mode==1?RT2860_H2M_BUSY:0;
 if(reg==2){
  if(mode==6)dma=true;
  if(mode==2 || (mode==4 && current==0x30) || (mode==5 && current==0x31))return 0xffffffffu;
  return (0xffffffffu & ~(0xffu<<(slot*8))) | (uint32_t(current)<<(slot*8));
 }
 if(reg==3)return (mode==3 || (mode==8 && current==0x30))?0:1u<<(slot*8);
 return 0;}
void RAL_WRITE(rt2860_softc*,int reg,uint32_t value){++writes;
 if(mode==7 && reg==3)dma=true;
 if(mode==10 && reg==4)dma=true;
 if(reg==1)mailboxes.push_back(value);
 if(reg==4){current=value;commands.push_back(value);}
 if(reg==2 || reg==3)clears.push_back(value);
}
void RAL_BARRIER_WRITE(rt2860_softc*){}
void DELAY(int){++delays;}
void reset(rt2860_softc &sc,int next){sc.io_failed=false;dma=false;mode=next;
 reads=writes=delays=0;commands.clear();mailboxes.clear();clears.clear();}
'''
t='''
int main(){rt2860_softc sc;
 assert(rt2860_mcu_cmd(&sc,7,0,1)==0 && !sc.io_failed);
 mode=1;reads=writes=delays=0;
 assert(rt2860_mcu_cmd(&sc,7,0,1)==EIO && sc.io_failed && reads==100 && writes==0);
 sc.io_failed=false;mode=2;reads=writes=delays=0;
 assert(rt2860_mcu_cmd(&sc,7,0,1)==ETIMEDOUT && sc.io_failed && reads==202);
 sc.io_failed=false;mode=3;assert(rt2860_mcu_cmd(&sc,7,0,1)==EIO && sc.io_failed);
 int old=reads;assert(rt2860_mcu_cmd(&sc,7,0,0)==EIO && reads==old);
 sc.io_failed=false;mode=0;assert(rt2860_mcu_cmd(&sc,7,0,0)==0);
 for(slot=0;slot<4;slot++) {
  reset(sc,0);assert(rt2860_mcu_cmd(&sc,7,0,1)==0 && !sc.io_failed);
 }
 slot=0;reset(sc,0);assert(rt2860_mcu_init_wakeup(&sc)==0 && !sc.io_failed);
 assert(commands==std::vector<uint32_t>({0x30,0x31}));
 assert((mailboxes[0]&0xffff)==0x02ff);
 reset(sc,4);assert(rt2860_mcu_init_wakeup(&sc)==0 && !sc.io_failed);
 assert(commands==std::vector<uint32_t>({0x30,0x31}) && delays==200 && clears.size()==4);
 for(auto value:clears)assert(value==0xffffffffu);
 reset(sc,4);assert(rt2860_mcu_cmd(&sc,0x30,0x02ff,1)==ETIMEDOUT && sc.io_failed);
 reset(sc,2);assert(rt2860_mcu_init_wakeup(&sc)==ETIMEDOUT && sc.io_failed);
 assert(commands==std::vector<uint32_t>({0x30,0x31}) && delays==400);
 reset(sc,5);assert(rt2860_mcu_init_wakeup(&sc)==ETIMEDOUT && sc.io_failed);
 reset(sc,1);assert(rt2860_mcu_init_wakeup(&sc)==EIO && commands.empty());
 reset(sc,8);assert(rt2860_mcu_init_wakeup(&sc)==EIO && sc.io_failed);
 assert(commands==std::vector<uint32_t>({0x30}));
 for(int fault:{6,7,10}) {
  reset(sc,fault);assert(rt2860_mcu_init_wakeup(&sc)==EIO && sc.io_failed);
  assert(commands==std::vector<uint32_t>({0x30}));
 }
 reset(sc,9);assert(rt2860_mcu_init_wakeup(&sc)==EIO && commands.empty() && reads==1);
 reset(sc,0);sc.io_failed=true;assert(rt2860_mcu_init_wakeup(&sc)==EIO && reads==0);
 reset(sc,0);dma=true;assert(rt2860_mcu_init_wakeup(&sc)==EIO && sc.io_failed && reads==0);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+t)
 exe=p/('test.exe' if os.name=='nt' else 'test')
 subprocess.run([os.environ.get('CXX','c++'),'-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS actual MCU helpers: four completion slots, strict command faults, bounded initial SLEEP timeout -> mandatory WAKEUP, failed WAKEUP, MMIO/DMA/removed-card fail-stop; host only.')
