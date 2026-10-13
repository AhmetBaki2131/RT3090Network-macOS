#!/usr/bin/env python3
"""Real publish snippet -> serialized registry -> real CLI -> real GUI (fake Tk)."""
from pathlib import Path
import subprocess,tempfile,json,plistlib,importlib.util,sys,types,runpy
r=Path(__file__).resolve().parent.parent
s=(r/'port/RT3090Network.cpp').read_text();a=s.index('    setProperty("RT3090ConnectionErrorCode"');b=s.index('    if(netif)',a);publish=s[a:b]
h=r'''
#include <cstdio>
#include <map>
#include <string>
#include "RTConnection.hpp"
struct Node {unsigned ni_rsn_supp_state,ni_rsn_retries=0,ni_rsnprotos=1,ni_rsncipher=8,ni_rsnakms=2;bool ni_port_valid;};
const unsigned IEEE80211_S_RUN=4;const int LINK_STATE_UP=4;
bool rtbsd_dma_failed(){return false;}
struct Controller {bool running=true;
 struct {bool io_failed=false;struct {unsigned ic_state=4;Node *ic_bss;struct {struct {int if_link_state=2;}ac_if;}ic_ac;}sc_ic;}chip;
 std::map<std::string,std::string> props;
 void setProperty(const char *key,unsigned value,int){props[key]=std::to_string(value);}
 void setProperty(const char *key,bool value){props[key]=value?"true":"false";}
 void publish(){
'''
t=r'''
 }
};
int main(){Controller c;Node n{};c.chip.sc_ic.ic_bss=&n;
 for(unsigned state=0;state<4;state++){
  n.ni_rsn_supp_state=state;n.ni_port_valid=(state==3);c.chip.sc_ic.ic_ac.ac_if.if_link_state=(state==3?4:2);c.publish();
  printf("{");bool first=true;for(auto &p:c.props){if(!first)printf(",");first=false;printf("\"%s\":%s",p.first.c_str(),p.second.c_str());}printf("}\n");
 }
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.cpp').write_text(h+publish+t)
 subprocess.run(['c++','-fsanitize=address,undefined','-I'+str(r/'port'),str(p/'test.cpp'),str(r/'port/RTConnection.cpp'),'-o',str(p/'test')],check=True)
 records=[json.loads(line) for line in subprocess.check_output([str(p/'test')]).splitlines()]
spec=importlib.util.spec_from_file_location('rt3090ctl',r/'tools/rt3090ctl.py');ctl=importlib.util.module_from_spec(spec);spec.loader.exec_module(ctl)
class Widget:
 def __init__(self,*a,**kw):self.value=''
 def pack(self,**kw):pass
 def title(self,*a):pass
 def geometry(self,*a):pass
 def insert(self,*a):pass
 def delete(self,*a):pass
 def bind(self,*a):pass
 def set(self,value):self.value=value
 def after(self,*a):pass
 def mainloop(self):pass
 def curselection(self):return ()
 def config(self,**kw):pass
tk=types.ModuleType('Tkinter')
for name in ['Tk','Label','Listbox','Entry','StringVar','Frame','Button']:setattr(tk,name,Widget)
mb=types.ModuleType('tkMessageBox');mb.showerror=lambda *a:None
sys.modules.update(Tkinter=tk,tkMessageBox=mb,rt3090ctl=ctl)
g=runpy.run_path(str(r/'tools/rt3090gui.py'));ns=g['render'].__globals__
for index,record in enumerate(records):
 record.update(RT3090Mode='network-experimental',RT3090InterfaceName='en2')
 ctl.subprocess.check_output=lambda args,value=record:plistlib.dumps([value])
 state=ctl.snapshot();g['render'](state)
 assert state['RT3090WPA2SupplicantState']==index
 assert 'WPA2: %s (%s)'%(index,ctl.supplicant_name(index)) in ns['status'].value
 assert 'Port authorized: %s'%(index==3) in ns['status'].value
print('PASS actual publish source -> registry XML -> CLI snapshot -> GUI render for 0/1/2/3 and port authorization; hardware handshake not exercised.')
