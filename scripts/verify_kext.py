#!/usr/bin/env python3
"""Check linked Mach-O kext structure; does not replace macOS kextutil."""
import json
import plistlib
import struct
import sys
from pathlib import Path

def inspect(bundle):
    info = plistlib.loads((bundle / "Contents/Info.plist").read_bytes())
    executable = bundle / "Contents/MacOS" / info["CFBundleExecutable"]
    data = executable.read_bytes()
    magic, cpu, subtype, kind, ncmds, cmdbytes, flags, reserved = struct.unpack_from("<8I", data)
    if magic != 0xfeedfacf or cpu != 0x1000007 or kind != 11:
        raise ValueError("Expected x86_64 MH_KEXT_BUNDLE, not executable/dylib/object")
    if 32 + cmdbytes > len(data):
        raise ValueError("Truncated Mach-O load commands")
    offset = 32
    commands = []
    symtab = None
    sections = []
    segments = []
    for _ in range(ncmds):
        cmd, length = struct.unpack_from("<II", data, offset)
        if length < 8 or offset + length > 32 + cmdbytes:
            raise ValueError("Invalid load-command bounds")
        commands.append(cmd)
        if cmd in (0xc, 0x18, 0x80000018, 0x8000001f, 0x80000028, 0xe):
            raise ValueError("Unexpected dylib, dylinker or LC_MAIN dependency in kext")
        if cmd == 2:
            symtab = struct.unpack_from("<4I", data, offset + 8)
        if cmd == 0x19:
            vmaddr, vmsize, fileoff, filesize = struct.unpack_from("<4Q", data, offset+24)
            if fileoff + filesize > len(data):
                raise ValueError("Segment exceeds executable length")
            segments.append((vmaddr, fileoff, filesize))
            nsects = struct.unpack_from("<I", data, offset + 64)[0]
            if length != 72 + nsects * 80:
                raise ValueError("Invalid segment command size")
            for index in range(nsects):
                section = offset + 72 + index * 80
                name = data[section:section+16].split(b"\0")[0].decode()
                seg = data[section+16:section+32].split(b"\0")[0].decode()
                sections.append(seg + "," + name)
        offset += length
    if offset != 32 + cmdbytes or symtab is None:
        raise ValueError("Missing symbol table or incorrect command size")
    symoff, nsyms, stroff, strsize = symtab
    if symoff + nsyms*16 > len(data) or stroff + strsize > len(data):
        raise ValueError("Invalid symbol-table bounds")
    strings = data[stroff:stroff+strsize]
    defined, imported = {}, []
    for index in range(nsyms):
        string_index, ntype, section, description, value = struct.unpack_from("<IBBHQ", data, symoff+index*16)
        if string_index >= len(strings):
            raise ValueError("Invalid symbol-name offset")
        name = strings[string_index:].split(b"\0")[0].decode()
        if ntype & 0xe0:  # STAB debug symbol
            continue
        if (ntype & 0xe) == 0 and value == 0:
            imported.append(name)
        else:
            defined[name] = value
    for symbol in ["_kmod_info", "__start", "__stop", "__realmain", "__antimain", "_rt_read_eeprom"]:
        if symbol not in defined:
            raise ValueError("Missing defined symbol " + symbol)
    if set(imported) & {"_memchr", "_kauth_cred_issuser"}:
        raise ValueError("Unsupported High Sierra imports: " + str(sorted(set(imported) & {"_memchr", "_kauth_cred_issuser"})))
    if any(name.startswith("_rt_") for name in imported):
        raise ValueError("Unresolved internal driver function")
    if info["CFBundleIdentifier"] == "org.rt3090.network":
        for name in imported:
            if any(part in name for part in ["ieee80211", "rt2860", "bus_dma", "pbkdf", "HMAC_", "SHA1", "rijndael", "taskq", "RT3090Timeout", "_fWorkloop", "_fCommandGate"]):
                raise ValueError("Unresolved network implementation: " + name)
    if any(name in {"___cxa_atexit", "_atexit", "___cxa_throw", "___gxx_personality_v0", "_main"} for name in imported):
        raise ValueError("Unexpected user-space C++ runtime import; compile with -fapple-kext")
    if info["CFBundleIdentifier"] == "org.rt3090.network":
        personality = next(iter(info["IOKitPersonalities"].values()))
        if personality.get("IOPCIPrimaryMatch") != "0x30901814" or personality.get("IOPCISecondaryMatch") != "0x1453103C" or "IOPCISubsystemMatch" in personality:
            raise ValueError("Incorrect supported PCI primary/secondary matching keys")
    driver_class = "RT3090Network" if info["CFBundleIdentifier"] == "org.rt3090.network" else "RT3090Diagnostic"
    if not any(driver_class in name for name in defined):
        raise ValueError("Missing compiled driver class")
    if not any("__mod_init_func" in section for section in sections):
        raise ValueError("Missing C++ constructor section")
    if not any("__mod_term_func" in section for section in sections):
        raise ValueError("Missing C++ destructor section for unload")
    if info["CFBundleIdentifier"] not in {"org.rt3090.experimental", "org.rt3090.network"}:
        raise ValueError("Wrong bundle identifier")
    metadata_address = defined["_kmod_info"]
    metadata = None
    for address, fileoff, filesize in segments:
        relative = metadata_address - address
        if 0 <= relative and relative + 196 <= filesize:
            metadata = data[fileoff+relative:fileoff+relative+196]
            break
    if metadata is None:
        raise ValueError("kmod metadata is not backed by file data")
    if struct.unpack_from("<I", metadata, 8)[0] != 1:
        raise ValueError("Incorrect kmod info version")
    if metadata[16:80].split(b"\0")[0].decode() != info["CFBundleIdentifier"]:
        raise ValueError("kmod identifier differs from Info.plist")
    if metadata[80:144].split(b"\0")[0].decode() != info["CFBundleVersion"]:
        raise ValueError("kmod version differs from Info.plist")
    start, stop = struct.unpack_from("<2Q", metadata, 180)
    if start != defined["__start"] or stop != defined["__stop"]:
        raise ValueError("Incorrect kmod start/stop entry pointers")
    return dict(binary_type="MH_KEXT_BUNDLE", architecture="x86_64", executable_bytes=len(data),
                defined_symbols=len(defined), kernel_imports=len(imported), imported_symbols=sorted(imported),
                kmod_metadata="identifier/version/start/stop validated", sections=sections, load_commands=commands,
                validation="structure only; macOS linking/loading/hardware untested")

if __name__ == "__main__":
    print(json.dumps(inspect(Path(sys.argv[1])), indent=2))
