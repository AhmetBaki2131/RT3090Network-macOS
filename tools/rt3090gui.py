#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
from __future__ import print_function
import threading,time,os
try:
    import Queue as queue
except ImportError:
    import queue
messages=queue.Queue()
try:
    import Tkinter as tk
    import tkMessageBox as messagebox
except ImportError:
    import tkinter as tk
    from tkinter import messagebox
import rt3090ctl as ctl
root=tk.Tk(); root.title('RT3090 Wi-Fi — experimental'); root.geometry('760x440')
label=tk.Label(root,text='Hardware validation pending. Request accepted does not mean connected.'); label.pack()
listing=tk.Listbox(root,width=110); listing.pack(fill='both',expand=True)
ssid=tk.Entry(root); ssid.pack(fill='x'); ssid.insert(0,'SSID')
password=tk.Entry(root,show='*'); password.pack(fill='x')
status=tk.StringVar(); tk.Label(root,textvariable=status,wraplength=730).pack()
results=[]
busy=False
auto_enabled=True
button_widgets=[]
def render(state):
    global results
    selection=listing.curselection()
    selected_bssid=ctl.as_bytes(results[int(selection[0])].get("BSSID",b"")) if selection and int(selection[0])<len(results) else None
    results=state.get('RT3090ScanResults',[]); listing.delete(0,'end')
    if state.get("RT3090Attached") is False:
        status.set("PCI card visible; driver not attached. Last start stage: %s (version %s)" % (state.get("RT3090LastStartError"),state.get("RT3090LastAttemptVersion")))
        return
    for e in results:
        signal=e.get('EstimatedRSSIdBm',0); signal=signal-0x100000000 if signal>=0x80000000 else signal
        bssid=':'.join('%02x'%v for v in bytearray(ctl.as_bytes(e.get('BSSID',b''))))
        listing.insert('end','%s  %s  ch %s  %s dBm  %s'%(ctl.as_bytes(e.get('SSID',b'')).decode('utf-8','replace'),bssid,e.get('Channel','?'),signal,e.get('Security','?')))
    if selected_bssid is not None:
        for index,entry in enumerate(results):
            if ctl.as_bytes(entry.get('BSSID',b''))==selected_bssid: listing.selection_set(index); break
    supp=state.get('RT3090WPA2SupplicantState'); error=state.get('RT3090ConnectionErrorCode',0)
    status.set('Mode: %s | Interface: %s | Association: %s | WPA2: %s (%s) | Port authorized: %s\nLast connection error: %s (%s) | EAPOL RX M1/M3: %s/%s | Queued M2/M4: %s/%s' % (
        state.get('RT3090Mode'),ctl.interface_name(state),state.get('RT3090AssociationState'),supp,ctl.supplicant_name(supp),state.get('RT3090ControlledPortAuthorized'),
        error,ctl.connection_error(error),state.get('RT3090EAPOLM1RX',0),state.get('RT3090EAPOLM3RX',0),state.get('RT3090EAPOLM2Queued',0),state.get('RT3090EAPOLM4Queued',0)))
def choose(event):
    sel=listing.curselection()
    if sel:
        ssid.delete(0,'end'); ssid.insert(0,ctl.as_bytes(results[int(sel[0])]['SSID']).decode('utf-8','replace'))
listing.bind('<<ListboxSelect>>',choose)
def submit(work, done=None):
    global busy
    if busy: return
    busy=True
    for button in button_widgets: button.config(state='disabled')
    status.set('Request in progress...')
    def worker():
        try: messages.put((done, work(), None))
        except Exception as e: messages.put((None, None, str(e)))
    thread=threading.Thread(target=worker); thread.daemon=True; thread.start()
def refresh():
    global auto_enabled
    auto_enabled=True; submit(ctl.snapshot, render)
def scan():
    def finished(value):
        status.set('Scan requested; waiting for results')
        root.after(6000,safe_refresh)
    submit(lambda:ctl.request('scan'),finished)
def connect():
    sel=listing.curselection()
    name=ctl.as_bytes(results[int(sel[0])]['SSID']) if sel else ctl.utf8_bytes(ssid.get())
    secret=ctl.utf8_bytes(password.get()); password.delete(0,'end')
    if not 1<=len(name)<=32 or not 8<=len(secret)<=63 or b'\0' in secret:
        raise RuntimeError('SSID 1..32 bytes; WPA2 password 8..63 bytes required')
    submit(lambda:ctl.request('join',name,secret),
           lambda value:status.set('Request accepted; connection and Internet are not yet verified'))
def action(fn):
    try: fn()
    except Exception as e: messagebox.showerror('RT3090',str(e))
def safe_refresh():
    if not busy: action(refresh)
def disconnect(): submit(lambda:ctl.request('disconnect'),lambda value:status.set('Disconnected'))
def dhcp(): submit(lambda:ctl.connectivity(True),lambda value:status.set('DHCP requested; use Check after a few seconds'))
def check():
    submit(lambda:ctl.connectivity(False),
           lambda value:status.set('IP and HTTPS checks passed; DNS uses the system resolver'))
buttons=tk.Frame(root); buttons.pack()
for title,fn in [('Scan',scan),('Connect',connect),('Disconnect',disconnect),('Status',refresh),('DHCP',dhcp),('Check',check)]:
    button=tk.Button(buttons,text=title,command=lambda f=fn:action(f))
    button.pack(side='left'); button_widgets.append(button)
def poll():
    global busy,auto_enabled
    try:
        while True:
            done,value,error=messages.get_nowait()
            busy=False
            for button in button_widgets: button.config(state='normal')
            if error:
                auto_enabled=False # avoid repeated modal errors from polling an absent driver
                status.set(error); messagebox.showerror('RT3090',error)
            elif done: action(lambda:done(value))
    except queue.Empty: pass
    root.after(200,poll)
def auto_refresh():
    if not busy and auto_enabled: action(refresh)
    root.after(1000,auto_refresh)
root.after(200,safe_refresh); root.after(200,poll); root.after(1000,auto_refresh); root.mainloop()
