#!/usr/bin/env python3
"""Generate an opt-in firmware include; no download or license alteration."""
import argparse
import hashlib
from pathlib import Path

EXPECTED_SHA256 = "67d5e8b32293cc2f31f67ebb112d4dabf1e23019a11c517036ba42cb48e4159c"

def validate(data):
    if len(data) != 8192:
        raise ValueError("RT3090 PCI firmware must be exactly 8192 bytes")
    crc = 0xffff
    for byte in data[:-2]:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8408 if crc & 1 else 0)
    if data[-2:] != bytes((crc & 255, crc >> 8)):
        raise ValueError("Firmware Linux CRC mismatch")
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Image differs from the pinned, inspected rt2860.bin; review provenance before updating the pin")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--firmware", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    text = "/* Generated; never edit. Firmware retains its separate Ralink license. */\n#define RT3090_HAS_FIRMWARE 0\n"
    if args.firmware:
        data = args.firmware.read_bytes()
        validate(data)
        rows = [", ".join("0x%02x" % byte for byte in data[i:i+16]) for i in range(0, len(data), 16)]
        text = "/* Unmodified firmware bytes; see licenses/LICENCE.ralink-firmware.txt. */\n#define RT3090_HAS_FIRMWARE 1\nstatic const uint8_t rt3090_firmware[8192] = {\n" + ",\n".join(rows) + "\n};\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)

if __name__ == "__main__":
    main()
