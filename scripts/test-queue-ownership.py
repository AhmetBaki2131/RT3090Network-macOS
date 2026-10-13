#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess
r=Path(__file__).resolve().parent.parent
s=(r/'port/RTIfq.cpp').read_text().replace('#include <sys/_ifq.h>','').replace('#include <sys/errno.h>','')
h='''
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
struct packet {};using mbuf_t=packet*;int freed=0;
void mbuf_freem(packet *p){++freed;free(p);}
struct IOPacketQueue {
 packet *slot=nullptr;unsigned capacity=1;
 static IOPacketQueue *withCapacity(unsigned n){auto *q=new IOPacketQueue;q->capacity=n;return q;}
 void setCapacity(unsigned n){capacity=n;}
 bool lockEnqueue(packet *p){if(!capacity||slot)return false;slot=p;return true;}
 packet *lockDequeue(){auto *p=slot;slot=nullptr;return p;}
 unsigned getSize(){return slot?1:0;}
 void lockFlush(){if(slot){mbuf_freem(slot);slot=nullptr;}}
 void release(){lockFlush();delete this;}
};
struct _ifqueue {IOPacketQueue *queue=nullptr;unsigned ifq_oactive=0;};struct _ifnet {};
'''
t='''
int main(){_ifqueue q;
 assert(ifq_empty(&q)&&ifq_len(&q)==0&&!ifq_dequeue(&q));
 assert(ifq_enqueue(&q,(packet*)malloc(sizeof(packet)))==ENOBUFS&&freed==1);
 ifq_init(&q,nullptr,1);assert(ifq_enqueue(&q,(packet*)malloc(sizeof(packet)))==0);
 assert(!ifq_empty(&q)&&ifq_len(&q)==1);
 assert(ifq_enqueue(&q,(packet*)malloc(sizeof(packet)))==ENOBUFS&&freed==2);
 assert(ifq_enqueue(&q,nullptr)==EINVAL);
 mbuf_freem(ifq_dequeue(&q));assert(freed==3&&ifq_empty(&q));
 ifq_destroy(&q);ifq_destroy(&q);assert(!q.queue);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+s+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real queue fork: empty/missing queue, full drop, consumes once, successful transfer, null packet, repeated destroy; host only.')
