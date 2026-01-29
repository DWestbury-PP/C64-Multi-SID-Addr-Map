#!/usr/bin/env python3
"""
HVSC Multi-SID Scanner

Scans the High Voltage SID Collection (HVSC) for multi-SID tunes (2SID, 3SID)
and extracts the SID chip addresses from the PSID/RSID file headers.

Usage:
    python hvsc_multisid.py /path/to/HVSC
    python hvsc_multisid.py /path/to/HVSC --output results.csv
    uv run hvsc_multisid.py /path/to/HVSC
"""

import argparse
import csv
import os
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# PSID/RSID header offsets and sizes
HEADER_MAGIC = 0x00        # 4 bytes: 'PSID' or 'RSID'
HEADER_VERSION = 0x04      # 2 bytes: version (1-4)
HEADER_DATA_OFFSET = 0x06  # 2 bytes: offset to data
HEADER_TITLE = 0x16        # 32 bytes: song title
HEADER_AUTHOR = 0x36       # 32 bytes: author name
HEADER_RELEASED = 0x56     # 32 bytes: release info
HEADER_SID2_ADDR = 0x7A    # 1 byte: second SID address (v3+)
HEADER_SID3_ADDR = 0x7B    # 1 byte: third SID address (v4+)

# Minimum header size for v2+ (which includes the address fields)
MIN_HEADER_SIZE_V2 = 0x7C


@dataclass
class SIDFile:
    """Represents a parsed multi-SID file."""
    filename: str
    relative_path: str
    sid_type: str
    title: str
    author: str
    released: str
    sid1_address: str
    sid2_address: str
    sid3_address: str
    version: int


def decode_sid_address(addr_byte: int) -> str:
    """
    Convert a SID address byte to the full address string.

    The byte represents the middle part of $Dxx0.
    Valid ranges: 0x42-0x7F ($D420-$D7F0) and 0xE0-0xFE ($DE00-$DFE0)
    0x00 or invalid values mean no SID at this slot.
    """
    if addr_byte == 0x00:
        return ""

    # Check valid ranges
    if (0x42 <= addr_byte <= 0x7F) or (0xE0 <= addr_byte <= 0xFE):
        # Only even values are valid
        if addr_byte % 2 == 0:
            return f"$D{addr_byte:02X}0"

    return ""


def read_string(data: bytes, offset: int, length: int) -> str:
    """Read a null-terminated or fixed-length string from binary data."""
    raw = data[offset:offset + length]
    # Find null terminator if present
    null_pos = raw.find(b'\x00')
    if null_pos != -1:
        raw = raw[:null_pos]
    # Decode as Windows-1252 (as per PSID spec), fallback to latin-1
    try:
        return raw.decode('windows-1252').strip()
    except UnicodeDecodeError:
        return raw.decode('latin-1', errors='replace').strip()


def parse_sid_file(filepath: Path, hvsc_root: Path) -> Optional[SIDFile]:
    """
    Parse a SID file and extract header information.

    Returns None if the file is not a valid PSID/RSID file.
    """
    try:
        with open(filepath, 'rb') as f:
            header = f.read(MIN_HEADER_SIZE_V2)

        if len(header) < MIN_HEADER_SIZE_V2:
            return None

        # Check magic (PSID or RSID)
        magic = header[HEADER_MAGIC:HEADER_MAGIC + 4]
        if magic not in (b'PSID', b'RSID'):
            return None

        # Get version (big-endian)
        version = struct.unpack('>H', header[HEADER_VERSION:HEADER_VERSION + 2])[0]

        # Extract metadata
        title = read_string(header, HEADER_TITLE, 32)
        author = read_string(header, HEADER_AUTHOR, 32)
        released = read_string(header, HEADER_RELEASED, 32)

        # First SID is always at $D400
        sid1_address = "$D400"

        # Second and third SID addresses (only valid for v3+ and v4+)
        sid2_address = ""
        sid3_address = ""

        if version >= 3:
            sid2_addr_byte = header[HEADER_SID2_ADDR]
            sid2_address = decode_sid_address(sid2_addr_byte)

        if version >= 4:
            sid3_addr_byte = header[HEADER_SID3_ADDR]
            sid3_address = decode_sid_address(sid3_addr_byte)

        # Determine SID type from filename
        filename = filepath.name
        filename_upper = filename.upper()
        if '3SID' in filename_upper:
            sid_type = '3SID'
        elif '2SID' in filename_upper:
            sid_type = '2SID'
        elif '4SID' in filename_upper:
            sid_type = '4SID'
        else:
            sid_type = 'Unknown'

        # Calculate relative path from HVSC root
        try:
            relative_path = filepath.relative_to(hvsc_root)
        except ValueError:
            relative_path = filepath

        return SIDFile(
            filename=filename,
            relative_path=str(relative_path),
            sid_type=sid_type,
            title=title,
            author=author,
            released=released,
            sid1_address=sid1_address,
            sid2_address=sid2_address,
            sid3_address=sid3_address,
            version=version,
        )

    except (IOError, OSError, struct.error) as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return None


def find_multisid_files(hvsc_path: Path) -> list[Path]:
    """Find all multi-SID files in the HVSC directory."""
    patterns = ['*2SID*', '*3SID*', '*4SID*']
    files = []

    for pattern in patterns:
        # Case-insensitive search using glob with recursive
        for filepath in hvsc_path.rglob('*.sid'):
            filename_upper = filepath.name.upper()
            if '2SID' in filename_upper or '3SID' in filename_upper or '4SID' in filename_upper:
                if filepath not in files:
                    files.append(filepath)

    return sorted(files)


def print_summary(sid_files: list[SIDFile]) -> None:
    """Print summary statistics about the scanned files."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Count by type
    type_counts = {}
    for sf in sid_files:
        type_counts[sf.sid_type] = type_counts.get(sf.sid_type, 0) + 1

    print(f"\nTotal multi-SID files found: {len(sid_files)}")
    print("\nBy type:")
    for sid_type in sorted(type_counts.keys()):
        print(f"  {sid_type}: {type_counts[sid_type]}")

    # Count by address combinations
    addr_combos = {}
    for sf in sid_files:
        combo = f"{sf.sid1_address}"
        if sf.sid2_address:
            combo += f" + {sf.sid2_address}"
        if sf.sid3_address:
            combo += f" + {sf.sid3_address}"
        addr_combos[combo] = addr_combos.get(combo, 0) + 1

    print("\nBy SID address configuration:")
    for combo in sorted(addr_combos.keys(), key=lambda x: (-addr_combos[x], x)):
        print(f"  {combo}: {addr_combos[combo]}")

    # Files with missing/unknown addresses
    missing_addr = [sf for sf in sid_files if not sf.sid2_address]
    if missing_addr:
        print(f"\nFiles with unspecified 2nd SID address: {len(missing_addr)}")
        print("  (These may be older PSID v1/v2 files without address fields)")


def write_csv(sid_files: list[SIDFile], output_path: Path) -> None:
    """Write the results to a CSV file."""
    fieldnames = [
        'filename',
        'relative_path',
        'type',
        'title',
        'author',
        'released',
        'sid1_address',
        'sid2_address',
        'sid3_address',
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for sf in sid_files:
            writer.writerow({
                'filename': sf.filename,
                'relative_path': sf.relative_path,
                'type': sf.sid_type,
                'title': sf.title,
                'author': sf.author,
                'released': sf.released,
                'sid1_address': sf.sid1_address,
                'sid2_address': sf.sid2_address,
                'sid3_address': sf.sid3_address,
            })


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scan HVSC for multi-SID tunes and extract SID addresses.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/HVSC
  %(prog)s /path/to/HVSC --output my_results.csv
  %(prog)s /path/to/HVSC --quiet
        """
    )

    parser.add_argument(
        'hvsc_path',
        type=Path,
        help='Path to the HVSC root directory'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('multisid_files.csv'),
        help='Output CSV file path (default: multisid_files.csv)'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress output (still shows summary)'
    )

    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Skip printing summary statistics'
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )

    args = parser.parse_args()

    # Validate HVSC path
    hvsc_path = args.hvsc_path.resolve()
    if not hvsc_path.exists():
        print(f"Error: HVSC path does not exist: {hvsc_path}", file=sys.stderr)
        return 1

    if not hvsc_path.is_dir():
        print(f"Error: HVSC path is not a directory: {hvsc_path}", file=sys.stderr)
        return 1

    # Find multi-SID files
    if not args.quiet:
        print(f"Scanning HVSC at: {hvsc_path}")
        print("Searching for multi-SID files...")

    files = find_multisid_files(hvsc_path)

    if not files:
        print("No multi-SID files found.", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Found {len(files)} multi-SID files. Parsing headers...")

    # Parse all files
    sid_files = []
    for i, filepath in enumerate(files):
        if not args.quiet and (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(files)}...")

        result = parse_sid_file(filepath, hvsc_path)
        if result:
            sid_files.append(result)

    if not sid_files:
        print("Error: Could not parse any SID files.", file=sys.stderr)
        return 1

    # Write CSV
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    write_csv(sid_files, output_path)

    if not args.quiet:
        print(f"\nResults written to: {output_path}")

    # Print summary
    if not args.no_summary:
        print_summary(sid_files)

    return 0


if __name__ == '__main__':
    sys.exit(main())
