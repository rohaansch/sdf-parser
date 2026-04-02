"""Basic usage examples for sdf_parser."""

from sdf_parser import SDFParser, format_entries

# --- 1. Parse a single file ---
parser = SDFParser()
sdf = parser.read("../tests/sample.sdf")

print(repr(sdf))
# SDF(cells=4, files=1, header=['SDFVERSION', 'DESIGN', ...])

# --- 2. Inspect the header ---
print(sdf.header_data["TIMESCALE"])   # 1ps

# --- 3. List all cells ---
print(list(sdf.cells.keys()))
# ['INV_X1', 'AND2_X1', 'DFFS_X2', 'MUX2_X1']

# --- 4. Print all entries for one cell ---
for entry in sdf.cells["INV_X1"]:
    print(entry)
# ['IOPATH', 'A', 'ZN', 2]
# ['COND', "A==1'b0", 'A', 'ZN', 1]
# ...

# --- 5. Extract a single cell (stops parsing early) ---
parser.reset()
sdf_inv = parser.read("../tests/sample.sdf", given_cell="INV_X1")
print(list(sdf_inv.cells.keys()))   # ['INV_X1']

# --- 6. Pretty-print entries ---
print(format_entries(sdf.cells["DFFS_X2"]))
