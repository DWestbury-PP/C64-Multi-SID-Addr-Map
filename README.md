# HVSC Multi-SID Address Scanner

A command-line tool to scan the [High Voltage SID Collection (HVSC)](https://hvsc.c64.org/) for multi-SID tunes and extract the SID chip addresses from PSID/RSID file headers.

## Why?

Users who enjoy multi-SID tracks on real Commodore 64 hardware typically need to:
1. Load each track individually to determine what SID addresses are required
2. Make hardware jumper setting changes on customized systems

This tool provides that information upfront, saving time and making it easy to prepare your hardware configuration before loading a tune.

## Features

- Scans HVSC for all multi-SID files (2SID, 3SID, 4SID)
- Extracts SID addresses directly from PSID/RSID v3/v4 headers
- Outputs results to CSV for easy sharing and parsing
- Shows summary statistics by type and address configuration
- Zero dependencies (pure Python standard library)

## Installation

### Using uv (recommended)

```bash
# Run directly without installing
uv run hvsc_multisid.py /path/to/HVSC

# Or install as a tool
uv tool install .
hvsc-multisid /path/to/HVSC
```

### Using pip

```bash
pip install .
hvsc-multisid /path/to/HVSC
```

### Direct execution

```bash
python3 hvsc_multisid.py /path/to/HVSC
```

## Usage

```bash
# Basic usage - outputs to multisid_files.csv
hvsc-multisid /path/to/HVSC

# Specify output file
hvsc-multisid /path/to/HVSC --output results.csv

# Quiet mode (no progress, still shows summary)
hvsc-multisid /path/to/HVSC --quiet

# Skip summary statistics
hvsc-multisid /path/to/HVSC --no-summary
```

## Output Format

The tool generates a CSV file with the following columns:

| Column | Description |
|--------|-------------|
| `filename` | SID file name |
| `relative_path` | Path relative to HVSC root |
| `type` | Multi-SID type (2SID, 3SID, 4SID) |
| `title` | Song title from header |
| `author` | Author/composer name |
| `released` | Release information |
| `sid1_address` | First SID address (always $D400) |
| `sid2_address` | Second SID address (e.g., $D420, $D500) |
| `sid3_address` | Third SID address (if applicable) |

## Example Output

```
Scanning HVSC at: /path/to/HVSC
Found 341 multi-SID files. Parsing headers...

Results written to: multisid_files.csv

============================================================
SUMMARY
============================================================

Total multi-SID files found: 341

By type:
  2SID: 314
  3SID: 27

By SID address configuration:
  $D400 + $D420: 194
  $D400 + $D500: 101
  $D400 + $D420 + $D440: 21
  $D400 + $DE00: 12
  ...
```

## Common SID Address Configurations

| Configuration | Description |
|---------------|-------------|
| $D400 + $D420 | Most common 2SID setup |
| $D400 + $D500 | Alternative 2SID (different I/O range) |
| $D400 + $D420 + $D440 | Common 3SID setup |
| $D400 + $DE00 | 2SID using extended I/O range |
| $D400 + $DE00 + $DF00 | 3SID using extended I/O range |

## Technical Details

The tool reads SID addresses from the PSID/RSID file header:
- **Offset 0x7A**: Second SID address (PSID v3+)
- **Offset 0x7B**: Third SID address (PSID v4+)

These bytes encode the middle portion of the address `$Dxx0`. For example:
- `0x42` → `$D420`
- `0x50` → `$D500`
- `0xE0` → `$DE00`

Valid ranges are `0x42-0x7F` ($D420-$D7F0) and `0xE0-0xFE` ($DE00-$DFE0).

## Requirements

- Python 3.8 or later
- No external dependencies

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [HVSC](https://hvsc.c64.org/) - The High Voltage SID Collection team
- [PSID/RSID File Format](https://hvsc.c64.org/download/C64Music/DOCUMENTS/SID_file_format.txt) - Format specification
