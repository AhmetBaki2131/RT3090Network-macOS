#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent.parent
s=(r/'port/ieee80211_proto.c').read_text();a=s.index('\nieee80211_proto_detach(')+1;b=s.index('{',a);depth=1;e=b+1
while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
f='void\n'+s[a:e]
h='''
#include <cassert>
#include <cstddef>
#define XYLog(...) ((void)0)
struct _ifnet{};struct Queue {int *mq_mtx=nullptr;};struct ieee80211com {Queue ic_mgtq,ic_pwrsaveq;};
int purged=0,freed=0;
void mq_purge(Queue *q){assert(q->mq_mtx);++purged;}
void IORecursiveLockFree(int *p){assert(p);++freed;delete p;}
'''
t='''
int main(){ieee80211com ic;ic.ic_mgtq.mq_mtx=new int;
 ieee80211_proto_detach((_ifnet*)&ic);assert(!ic.ic_mgtq.mq_mtx && purged==1 && freed==1);
 ieee80211_proto_detach((_ifnet*)&ic);assert(freed==1);
 ic.ic_mgtq.mq_mtx=new int;ic.ic_pwrsaveq.mq_mtx=new int;
 ieee80211_proto_detach((_ifnet*)&ic);assert(!ic.ic_pwrsaveq.mq_mtx&&freed==3&&purged==3);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+f+t)
 subprocess.run(['c++','-fsanitize=address,undefined',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real protocol detach: partial initialization, releases both queue locks, repeated cleanup without double free; host only.')
