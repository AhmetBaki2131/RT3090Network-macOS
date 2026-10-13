#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parent.parent
source=(r/'port/RTTimeout.cpp').read_text().replace('#include <sys/CTimeout.hpp>','')
shim=r'''
#include <cassert>
#include <cstdio>
using IOReturn=int;
const int kIOReturnSuccess=0,kIOReturnError=1,kIOReturnBadArgument=2,kIOReturnNoMemory=3;
#define IOLog(...) ((void)0)
#define OSDynamicCast(T,o) static_cast<T*>(o)
struct OSObject { virtual ~OSObject() {} };
struct IOTimerEventSource;
struct CTimeout: OSObject {
 int refs=1; static int destroyed;
 IOTimerEventSource *tm=nullptr; bool isPending=false;
 void (*to_func)(void*)=nullptr; void *to_arg=nullptr;
 bool init(){return true;} void retain(){++refs;} void release(){if(!--refs)delete this;}
 ~CTimeout(){++destroyed;}
 static void timeoutOccurred(OSObject*,IOTimerEventSource*);
 static IOReturn timeout_add_msec(OSObject*,void*,void*,void*,void*);
 static IOReturn timeout_del(OSObject*,void*,void*,void*,void*);
 static IOReturn timeout_free(OSObject*,void*,void*,void*,void*);
 static IOReturn timeout_set(OSObject*,void*,void*,void*,void*);
 static IOReturn timeout_pending(OSObject*,void*,void*,void*,void*);
}; int CTimeout::destroyed=0;
struct IOTimerEventSource {
 int canceled=0; bool enabled=false;
 static IOTimerEventSource *timerEventSource(OSObject*,void(*)(OSObject*,IOTimerEventSource*)) {return new IOTimerEventSource;}
 void enable(){enabled=true;} void disable(){enabled=false;}
 int setTimeoutMS(int){return 0;} void cancelTimeout(){++canceled;} void release(){delete this;}
};
struct IOWorkLoop { int added=0,removed=0; int addEventSource(IOTimerEventSource*){++added;return 0;}
 void removeEventSource(IOTimerEventSource*){++removed;} };
'''
t=r'''
int calls=0; void callback_fn(void*) {++calls;}
struct Context {CTimeout **slot; IOWorkLoop *wl;};
void self_free(void *arg) {
 auto *c=(Context*)arg; CTimeout::timeout_free(nullptr,c->slot,c->wl,nullptr,nullptr);
 assert(CTimeout::destroyed==0); // callback owner retained until return
}
int main(){
 CTimeout *to=nullptr; IOWorkLoop wl; int ms=1;
 assert(CTimeout::timeout_set(nullptr,&to,nullptr,nullptr,nullptr)==kIOReturnBadArgument);
 assert(!to);
 assert(CTimeout::timeout_set(nullptr,&to,(void*)callback_fn,nullptr,nullptr)==0);
 assert(CTimeout::timeout_add_msec(nullptr,&to,&wl,&ms,nullptr)==0);
 auto *timer=to->tm;
 CTimeout::timeoutOccurred(to,timer); assert(calls==1);
 CTimeout::timeoutOccurred(to,timer); assert(calls==1); // stale callback ignored
 CTimeout::timeout_add_msec(nullptr,&to,&wl,&ms,nullptr);
 CTimeout::timeout_set(nullptr,&to,(void*)callback_fn,nullptr,nullptr);
 assert(timer->canceled==1 && !to->isPending);
 CTimeout::timeoutOccurred(to,timer); assert(calls==1);
 Context ctx{&to,&wl};
 CTimeout::timeout_set(nullptr,&to,(void*)self_free,&ctx,nullptr);
 CTimeout::timeout_add_msec(nullptr,&to,&wl,&ms,nullptr);
 assert(CTimeout::timeout_free(nullptr,&to,nullptr,nullptr,nullptr)==kIOReturnBadArgument);
 assert(to && to->isPending);
 CTimeout::timeoutOccurred(to,timer);
 assert(!to && CTimeout::destroyed==1 && wl.added==1 && wl.removed==1);
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(shim+source+t)
 subprocess.run(['c++','-fsanitize=address,undefined','-g',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS real CTimeout: stale callback, reset/cancel, null callback/workloop, self-free lifetime; ASan/UBSan. IOKit shim only.')
