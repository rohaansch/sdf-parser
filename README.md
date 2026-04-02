# sdf-parser

A pure-Python parser for **Standard Delay Format (SDF)** files — the
industry-standard format used by EDA tools to back-annotate timing delays
and constraints onto digital designs.

[![CI](https://github.com/rohaansch/sdf-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/rohaansch/sdf-parser/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.7%2B-blue)](https://pypi.org/project/eda-sdf-parser/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Building a Python SDF Parser for EDA Flow Automation](https://rohanchadhury.medium.com/building-a-python-sdf-parser-for-eda-flow-automation-cc7f028faf35)
— Closing a tooling gap that every EDA engineer eventually runs into.

## Features

- Parses `IOPATH`, `COND`, `CONDELSE`, `WIDTH`, `SETUPHOLD`, and `RECREM`
- Single file **or** directory of SDF files (with cross-file consistency checks)
- Single-cell extraction mode — stops early once the target cell is found
- **Zero required dependencies** — only the Python standard library
- Optional colored warnings via [`termcolor`](https://pypi.org/project/termcolor/)
- CLI included: `sdf-parser timing.sdf --cell INV_X1`

## Installation

```bash
pip install eda-sdf-parser                  # no extra dependencies
pip install "eda-sdf-parser[color]"         # adds termcolor for colored warnings
```

[![PyPI](https://img.shields.io/pypi/v/eda-sdf-parser)](https://pypi.org/project/eda-sdf-parser/)
[![Python](https://img.shields.io/pypi/pyversions/eda-sdf-parser)](https://pypi.org/project/eda-sdf-parser/)

Or for development:

```bash
git clone https://github.com/rohaansch/sdf-parser
cd sdf-parser
pip install -e ".[dev]"
```

## Quick start

```python
from sdf_parser import SDFParser

parser = SDFParser()
sdf = parser.read("timing.sdf")

print(repr(sdf))
# SDF(cells=142, files=1, header=['SDFVERSION', 'DESIGN', 'TIMESCALE'])

for entry in sdf.cells["INV_X1"]:
    print(entry)
# ['IOPATH', 'A', 'ZN', 2]
# ['COND', "A==1'b0", 'A', 'ZN', 1]
# ['WIDTH', None, 'posedge', 'A', 1]
```

## Parsed entry format

Each entry in `sdf.cells["CELLNAME"]` is a list whose first element is the
construct keyword:

| Construct    | Entry format |
|---|---|
| `IOPATH`     | `[IOPATH, pin_1, pin_2, n]` |
| `COND`       | `[COND, condition, pin_1, pin_2, n]` |
| `CONDELSE`   | `[CONDELSE, pin_1, pin_2, n]` |
| `WIDTH`      | `[WIDTH, condition, edge, port, n]` |
| `SETUPHOLD`  | `[SETUPHOLD, cond_1, edge_1, port_1, cond_2, edge_2, port_2, n]` |
| `RECREM`     | `[RECREM, cond_1, edge_1, port_1, cond_2, edge_2, port_2, n]` |

`condition` is `None` when no `COND` qualifier is present.
`n` is the number of delay value tuples (e.g. `3` for min/typ/max).

### Full example

SDF input:

```
(CELL
  (CELLTYPE "DFFS_X2")
  (INSTANCE FF1)
  (TIMINGCHECK
    (SETUPHOLD (posedge D) (posedge CK) (0.1:0.1:0.1) (0.05:0.05:0.05))
    (RECREM   (negedge SN) (posedge CK) (0.2:0.2:0.2) (0.1:0.1:0.1))
    (WIDTH    (posedge CK) (0.3:0.3:0.3))
  )
)
```

Python output:

```python
sdf.cells["DFFS_X2"]
# [
#   ['SETUPHOLD', None, 'posedge', 'D', None, 'posedge', 'CK', 2],
#   ['RECREM',    None, 'negedge', 'SN', None, 'posedge', 'CK', 2],
#   ['WIDTH',     None, 'posedge', 'CK', 1],
# ]
```

## API reference

### `SDFParser(path=None)`

Create a parser.  `path` sets the default file/directory used by `read()`.

### `SDFParser.read(path=None, given_cell=None) → SDF`

| Argument | Type | Description |
|---|---|---|
| `path` | `str` | `.sdf` file or directory. Falls back to the constructor path. |
| `given_cell` | `str` | Extract only this cell (case-insensitive). |

Raises `ValueError` / `FileNotFoundError` / `IOError` on bad input.

### `SDFParser.reset()`

Clear internal state to reuse the parser for a different file:

```python
sdf_fast = parser.read("fast.sdf")
parser.reset()
sdf_slow = parser.read("slow.sdf")
```

### `SDF` object

| Attribute | Type | Description |
|---|---|---|
| `header_data` | `dict` | Header fields (`SDFVERSION`, `DESIGN`, `TIMESCALE`, …) |
| `cells` | `dict[str, list]` | Cell name → list of parsed entries |
| `files` | `list[str]` | All files that contributed to this object |

### `format_entries(cell) → str`

Format a cell's entries as a human-readable multi-line string:

```python
from sdf_parser import format_entries
print(format_entries(sdf.cells["INV_X1"]))
```

## Parsing a directory

When `path` is a directory every `.sdf` file inside it is parsed and merged.
Cells found in multiple files are compared; mismatches produce a warning:

```python
sdf = SDFParser().read("sdf_corners/")
print(repr(sdf))
# SDF(cells=142, files=3, header=['SDFVERSION', 'DESIGN', 'TIMESCALE'])
```

## Command-line usage

```
sdf-parser timing.sdf
sdf-parser timing.sdf --cell INV_X1
sdf-parser timing.sdf --cell INV_X1 --header
sdf-parser sdf_corners/ --header
sdf-parser --version
```

Or without installing:

```
python -m sdf_parser timing.sdf --cell INV_X1
```

## Limitations

- Delay values are not parsed — only the **count** of value tuples is stored.
- Only the constructs listed above are extracted; other SDF keywords are skipped.
- OASIS and binary SDF formats are not supported.

## Running the tests

```bash
pip install -e ".[dev]"
pytest -v
```

## License

[MIT](LICENSE)
