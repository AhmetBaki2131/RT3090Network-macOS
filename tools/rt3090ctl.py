#!/usr/bin/env python
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline High Sierra control tool, compatible with system Python 2.7/3.
Uses public IOKit/CoreFoundation APIs; does not install a kext or alter SIP.
"""
from __future__ import print_function
import argparse
import ctypes
import getpass
import os
import plistlib
import subprocess
import sys
import time
import socket
import ssl
import re
import struct

def _records(data):
    if not data.strip(): return []
    try:
        records=plistlib.loads(data) if hasattr(plistlib, "loads") else plistlib.readPlistFromString(data)
        if not isinstance(records,list): raise ValueError("expected an IORegistry record array")
        return records
    except Exception as exc:
        raise RuntimeError("ioreg returned invalid XML: %s" % exc)

def _pci_id(value):
    if isinstance(value, int): return value
    value=as_bytes(value)
    if isinstance(value, bytes) and len(value)>=4: return struct.unpack('<I',value[:4])[0]
    return None

def _find_card(records):
    for entry in records:
        if _pci_id(entry.get('vendor-id'))==0x1814 and _pci_id(entry.get('device-id'))==0x3090:
            return entry
        found=_find_card(entry.get('IORegistryEntryChildren',[]))
        if found: return found
    return None

def snapshot():
    data = subprocess.check_output(["/usr/sbin/ioreg", "-r", "-c", "RT3090Network", "-a"])
    records=_records(data)
    if records:
        state=records[0]
        state['RT3090Attached']=True
        return state
    # Read PCI registry only; this never opens the card or starts radio/DMA.
    pci=_records(subprocess.check_output(["/usr/sbin/ioreg", "-r", "-c", "IOPCIDevice", "-a"]))
    card=_find_card(pci)
    if card:
        return {'RT3090Attached':False,'RT3090Mode':'not-attached',
                'RT3090Status':'PCI card visible; RT3090Network is not attached',
                'RT3090LastStartError':card.get('RT3090LastStartError','No start failure recorded; matching/start must be checked'),
                'RT3090LastAttemptVersion':card.get('RT3090LastAttemptVersion','unknown'),
                'RT3090PCINode':card.get('IORegistryEntryName',card.get('IOName','pci1814,3090'))}
    raise RuntimeError("RT3090Network node is absent and PCI 1814:3090 was not found; no hardware access attempted.")

def request(command, ssid=None, password=None):
    if os.geteuid() != 0:
        raise RuntimeError("Use sudo for scan/join/disconnect requests.")
    print("RT3090 control: %s request begin" % command); sys.stdout.flush()
    state=snapshot()
    if state.get("RT3090Attached") is False:
        raise RuntimeError("Driver not attached: %s" % state.get("RT3090LastStartError","unknown start stage"))
    if state.get("RT3090Mode") == "pci-diagnostic":
        raise RuntimeError("PCI-only diagnostic mode: scan/join/disconnect are disabled. Use status.")
    if state.get("RT3090HardwareFailed") and command in ("scan", "join"):
        raise RuntimeError("Driver stopped after a hardware/DMA fault; do not automatically retry Connect. Save status and kernel logs.")
    interface=interface_name(state)
    if command in ("scan","join") and (not interface or not re.match(r"^en[0-9]+$",interface)):
        raise RuntimeError("Attached driver has no published BSD interface; refusing radio request")
    if command in ("scan","join") and interface and re.match(r"^en[0-9]+$",interface):
        subprocess.check_call(["/sbin/ifconfig",interface,"up"])
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    io = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
    ptr = ctypes.c_void_p
    cf.CFStringCreateWithCString.argtypes = [ptr, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFStringCreateWithCString.restype = ptr
    cf.CFDataCreate.argtypes = [ptr, ptr, ctypes.c_long]
    cf.CFDataCreate.restype = ptr
    cf.CFDictionaryCreate.argtypes = [ptr, ptr, ptr, ctypes.c_long, ptr, ptr]
    cf.CFDictionaryCreate.restype = ptr
    cf.CFRelease.argtypes = [ptr]
    io.IOServiceMatching.argtypes = [ctypes.c_char_p]
    io.IOServiceMatching.restype = ptr
    io.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, ptr]
    io.IOServiceGetMatchingService.restype = ctypes.c_uint32
    io.IORegistryEntrySetCFProperties.argtypes = [ctypes.c_uint32, ptr]
    io.IORegistryEntrySetCFProperties.restype = ctypes.c_int
    io.IOObjectRelease.argtypes = [ctypes.c_uint32]
    service = io.IOServiceGetMatchingService(0, io.IOServiceMatching(b"RT3090Network"))
    if not service:
        raise RuntimeError("RT3090Network service was not found.")
    allocations = []
    buffers = []
    dictionary = None
    try:
        names, values = [], []
        for name, value in [(b"Command", command.encode("ascii")), (b"SSID", ssid), (b"Password", password)]:
            if value is None:
                continue
            key = cf.CFStringCreateWithCString(None, name, 0x08000100)
            if name == b"Command":
                entry = cf.CFStringCreateWithCString(None, value, 0x08000100)
            else:
                buffer = ctypes.create_string_buffer(value)
                buffers.append(buffer)
                entry = cf.CFDataCreate(None, ctypes.cast(buffer, ptr), len(value))
            if key: allocations.append(key)
            if entry: allocations.append(entry)
            if not key or not entry:
                raise RuntimeError("Unable to allocate request.")
            names.append(key); values.append(entry)
        keys = (ptr * len(names))(*names); entries = (ptr * len(values))(*values)
        # No callbacks: keep all CF values alive until the synchronous request returns.
        dictionary = cf.CFDictionaryCreate(None, keys, entries, len(names), None, None)
        if not dictionary:
            raise RuntimeError("Unable to allocate request dictionary.")
        print("RT3090 control: %s calling driver" % command); sys.stdout.flush()
        result = io.IORegistryEntrySetCFProperties(service, dictionary)
        print("RT3090 control: %s driver returned 0x%08x" % (command,result & 0xffffffff)); sys.stdout.flush()
        if result:
            raise RuntimeError("Driver rejected request: 0x%08x" % (result & 0xffffffff))
    finally:
        if dictionary:
            cf.CFRelease(dictionary)
        for allocation in allocations:
            cf.CFRelease(allocation)
        for buffer in buffers:
            ctypes.memset(ctypes.addressof(buffer), 0, ctypes.sizeof(buffer))
        io.IOObjectRelease(service)

def as_bytes(data):
    if hasattr(data, "data"):
        return data.data
    return data

def utf8_bytes(text):
    return text if isinstance(text, bytes) else text.encode("utf-8")

def supplicant_name(value):
    return {0:'INITIALIZE',1:'WAIT_M1',2:'M2_QUEUED_WAIT_M3',3:'M4_QUEUED_KEYS_PENDING'}.get(value,'unknown')
def connection_error(value):
    return {0:'none',101:'scan timeout',102:'authentication timeout',103:'association timeout',
            104:'no valid EAPOL M1',105:'no valid EAPOL M3',106:'controlled port not authorized',
            201:'AP rejected authentication',202:'AP rejected association',203:'M1 received in INITIALIZE',
            301:'M2 queue failed',302:'M4 queue failed',303:'EAPOL MIC verification failed',304:'key install failed'}.get(value,'unknown')

def show_networks():
    state = snapshot()
    if state.get("RT3090Attached") is False:
        print("Mode: not attached (this is not a WPA2 error)")
        print("Driver status:",state.get("RT3090Status"))
        print("Last start stage:",state.get("RT3090LastStartError"))
        print("Last attempted version:",state.get("RT3090LastAttemptVersion"))
        return
    if state.get("RT3090Mode") == "pci-diagnostic":
        print("Mode: PCI-only diagnostic; firmware/DMA/IRQ/radio not started")
        for key in ["RT3090VendorID", "RT3090DeviceID", "RT3090SubsystemVendorID", "RT3090SubsystemID", "RT3090PCIRevision"]:
            value = state.get(key)
            print(key + ":", "0x%04x" % value if isinstance(value, int) else value)
        print("PCI matched:", state.get("RT3090PCIMatched", False))
        print("No network interface or Wi-Fi results are expected in this mode.")
        return
    for entry in state.get("RT3090ScanResults", []):
        ssid = as_bytes(entry.get("SSID", b"")).decode("utf-8", "replace")
        bssid = ":".join("%02x" % v for v in bytearray(as_bytes(entry.get("BSSID", b""))))
        signal = entry.get("EstimatedRSSIdBm")
        if signal is not None and signal >= 0x80000000: signal -= 0x100000000
        print("%s  channel %s  %s dBm  %s  %s" % (bssid,entry.get("Channel","?"),signal,entry.get("Security","unknown"),ssid or "<hidden SSID>"))
    print("Mode:",state.get("RT3090Mode","legacy"))
    print("Interface:",interface_name(state) or "not published")
    print("Driver status:",state.get("RT3090Status","unknown"))
    print("Hardware failure:",state.get("RT3090HardwareFailed",False))
    supp=state.get("RT3090WPA2SupplicantState")
    print("Supplicant state:",supp,supplicant_name(supp))
    error=state.get("RT3090ConnectionErrorCode",0)
    print("Last connection error:",error,connection_error(error),"Peer status:",state.get("RT3090PeerStatusCode",0))
    print("EAPOL M1 RX / M2 queued / M3 RX / M4 queued:",state.get("RT3090EAPOLM1RX",0),state.get("RT3090EAPOLM2Queued",0),state.get("RT3090EAPOLM3RX",0),state.get("RT3090EAPOLM4Queued",0))
    print("EAPOL TX queue failures:",state.get("RT3090EAPOLTXFailures",0),"EAPOL hardware submissions:",state.get("RT3090EAPOLHardwareTXSubmitted",0),"Hardware TX frames:",state.get("RT3090HardwareTXSubmitted",0),"Bad MIC:",state.get("RT3090BadMICCount",0))
    print("RSN enabled:",state.get("RT3090RSNEnabled"),"Selected proto/cipher/AKM:",state.get("RT3090SelectedRSNProtocol"),state.get("RT3090SelectedCipher"),state.get("RT3090SelectedAKM"))
    print("Controlled port authorized:",state.get("RT3090ControlledPortAuthorized",False))
    print("EAPOL retries:",state.get("RT3090EAPOLRetries","unknown"))
    print("Association state:", state.get("RT3090AssociationState", "unknown"))
    link=state.get("RT3090LinkState")
    print("Link state:", {0:"unknown",1:"invalid",2:"down",3:"keepalive down",4:"up",5:"half duplex",6:"full duplex"}.get(link,"unknown"), "(this is not an Internet test)")

def interface_name(node):
    name=node.get("RT3090InterfaceName") or node.get("BSD Name")
    if name: return name
    for child in node.get("IORegistryEntryChildren",[]):
        name=interface_name(child)
        if name: return name
    return None

def connectivity(dhcp=False):
    state=snapshot(); interface=interface_name(state)
    if not interface or not re.match(r"^en[0-9]+$",interface):
        raise RuntimeError("RT3090 interface BSD name not found")
    if not state.get("RT3090ControlledPortAuthorized",False):
        raise RuntimeError("WPA2 controlled port is not authorized yet")
    if dhcp:
        if os.geteuid()!=0: raise RuntimeError("DHCP request requires sudo")
        subprocess.check_call(["/usr/sbin/ipconfig","set",interface,"DHCP"])
        print("DHCP request submitted for",interface,"; use check after a few seconds")
        return
    address=subprocess.check_output(["/usr/sbin/ipconfig","getifaddr",interface]).decode().strip()
    route=subprocess.check_output(["/sbin/route","-n","get","1.1.1.1"]).decode()
    if not re.search(r"interface:\s*"+re.escape(interface)+r"\s",route):
        raise RuntimeError("Route to test IP does not use RT3090; refusing false Internet success")
    print("IPv4:",address,"Interface:",interface)
    subprocess.check_call(["/sbin/ping","-S",address,"-c","3","-W","2000","1.1.1.1"])
    addresses=socket.getaddrinfo("example.com",443,socket.AF_INET)
    destination=addresses[0][4][0]
    print("System DNS resolved example.com:",destination)
    webroute=subprocess.check_output(["/sbin/route","-n","get",destination]).decode()
    if not re.search(r"interface:\s*"+re.escape(interface)+r"\s",webroute):
        raise RuntimeError("HTTPS route does not use RT3090")
    transport=socket.create_connection((destination,443),10,(address,0))
    tls=None
    try:
        tls=ssl.create_default_context().wrap_socket(transport,server_hostname="example.com")
        tls.sendall(b"HEAD / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n")
        response=tls.recv(1024)
        if not response.startswith(b"HTTP/"): raise RuntimeError("No valid HTTPS response")
        print("HTTPS response:",response.split(b"\r\n",1)[0].decode("ascii","replace"))
    finally:
        if tls: tls.close()
        else: transport.close()
    print("IP traffic test used RT3090. DNS uses the system resolver; inspect scutil --dns for its path.")

def main():
    parser = argparse.ArgumentParser(description="RT3090 experimental network control")
    parser.add_argument("command", choices=["scan", "list", "join", "connect", "disconnect", "status", "dhcp", "check"])
    parser.add_argument("ssid", nargs="?")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This tool runs only on macOS.")
    if args.command in ("dhcp", "check"):
        connectivity(args.command=="dhcp"); return
    if args.command in ("list", "status"):
        show_networks(); return
    if args.command in ("join", "connect"):
        if not args.ssid:
            parser.error("join requires an SSID")
        ssid = utf8_bytes(args.ssid)
        password = utf8_bytes(getpass.getpass("WPA2 password (not stored in a file): "))
        if not 1 <= len(ssid) <= 32 or not 8 <= len(password) <= 63 or b"\0" in password:
            parser.error("SSID must be 1..32 bytes; passphrase 8..63 bytes, no NUL")
        request("join", ssid, password)
        print("Join request accepted. Use status and verify DHCP/traffic; success is not confirmed yet.")
    elif args.command == "scan":
        request("scan"); time.sleep(5); show_networks()
    else:
        request("disconnect"); print("Disconnect request accepted.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr); sys.exit(1)
