#!/usr/bin/env python3
"""Run actual GUI module with fake Tk: no macOS display available."""
import sys,types,threading,runpy,time
from pathlib import Path
main=threading.current_thread(); scheduled=[]
class Widget:
 def __init__(self,*args,**kwargs): self.state='normal'
 def assert_main(self): assert threading.current_thread() is main
 def pack(self,**kwargs): self.assert_main()
 def title(self,*args): self.assert_main()
 def geometry(self,*args): self.assert_main()
 def insert(self,*args): self.assert_main()
 def delete(self,*args): self.assert_main()
 def bind(self,*args): self.assert_main()
 def set(self,*args): self.assert_main();self.value=args[0]
 def config(self,**kw): self.assert_main();self.state=kw.get('state',self.state)
 def after(self,*args): self.assert_main();scheduled.append(args)
 def mainloop(self): self.assert_main()
 def curselection(self): self.assert_main();return ()
 def get(self): self.assert_main();return 'password123'
tk=types.ModuleType('Tkinter')
for name in ['Tk','Label','Listbox','Entry','StringVar','Frame','Button']: setattr(tk,name,Widget)
mb=types.ModuleType('tkMessageBox');errors=[]
def showerror(*args): assert threading.current_thread() is main; errors.append(args)
mb.showerror=showerror
ctl=types.ModuleType('rt3090ctl');ctl.utf8_bytes=lambda x:x.encode();ctl.as_bytes=lambda x:x
sys.modules.update(Tkinter=tk,tkMessageBox=mb,rt3090ctl=ctl)
r=Path(__file__).resolve().parent.parent
g=runpy.run_path(str(r/'tools/rt3090gui.py')); namespace=g['submit'].__globals__
ready=threading.Event(); release=threading.Event();calls=[];results=[]
def work():
 assert threading.current_thread() is not main;calls.append(1);ready.set();assert release.wait(2);return 42
g['submit'](work,lambda result:results.append(result));assert ready.wait(1)
assert all(b.state=='disabled' for b in namespace['button_widgets'])
g['submit'](lambda:calls.append(2));assert calls==[1]
release.set()
limit=time.time()+2
while namespace['messages'].empty() and time.time()<limit: threading.Event().wait(.005)
g['poll']();assert results==[42] and not namespace['busy']
assert all(b.state=='normal' for b in namespace['button_widgets'])
def failure(): raise RuntimeError('simulated driver failure')
g['submit'](failure)
limit=time.time()+2
while namespace['messages'].empty() and time.time()<limit: threading.Event().wait(.005)
g['poll']();assert errors and not namespace['busy'] and not namespace['auto_enabled']
g['render']({'RT3090Attached':False,'RT3090LastStartError':'EEPROM read','RT3090LastAttemptVersion':'0.3.4'})
assert 'not attached' in namespace['status'].value and 'EEPROM read' in namespace['status'].value
namespace['busy']=True;g['auto_refresh']();assert namespace['messages'].empty()
namespace['busy']=False;namespace['auto_enabled']=True;ctl.snapshot=lambda:{'RT3090Attached':False,'RT3090LastStartError':'EEPROM read'}
g['auto_refresh']();limit=time.time()+2
while namespace['messages'].empty() and time.time()<limit: threading.Event().wait(.005)
g['poll']();assert not namespace['busy'] and 'not attached' in namespace['status'].value
print('PASS actual GUI: background work, one request at a time, main-thread completion/errors, buttons restored. Native Tk/app untested.')
