"""Tests for sdf_parser."""

import os
import pytest

from sdf_parser import SDFParser, SDF, format_entries

SAMPLE_SDF = os.path.join(os.path.dirname(__file__), "sample.sdf")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sdf():
    return SDFParser().read(SAMPLE_SDF)


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------

class TestBasicParsing:
    def test_returns_sdf_instance(self, sdf):
        assert isinstance(sdf, SDF)

    def test_all_cells_present(self, sdf):
        assert set(sdf.cells.keys()) == {"INV_X1", "AND2_X1", "DFFS_X2", "MUX2_X1"}

    def test_files_populated(self, sdf):
        assert len(sdf.files) == 1
        assert sdf.files[0].endswith("sample.sdf")

    def test_repr(self, sdf):
        r = repr(sdf)
        assert "cells=4" in r
        assert "files=1" in r


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

class TestHeader:
    def test_sdfversion(self, sdf):
        assert sdf.header_data.get("SDFVERSION") == "OVI 3.0"

    def test_design(self, sdf):
        assert sdf.header_data.get("DESIGN") == "example_design"

    def test_timescale(self, sdf):
        assert sdf.header_data.get("TIMESCALE") == "1ps"


# ---------------------------------------------------------------------------
# INV_X1 — IOPATH and COND
# ---------------------------------------------------------------------------

class TestINV:
    def test_entry_count(self, sdf):
        # 1 IOPATH + 2 COND + 2 WIDTH = 5
        assert len(sdf.cells["INV_X1"]) == 5

    def test_iopath_format(self, sdf):
        iopath = sdf.cells["INV_X1"][0]
        assert iopath[0] == "IOPATH"
        assert iopath[1] == "A"
        assert iopath[2] == "ZN"
        assert isinstance(iopath[3], int)  # n_values

    def test_cond_format(self, sdf):
        cond = next(e for e in sdf.cells["INV_X1"] if e[0] == "COND")
        assert len(cond) == 5          # [COND, condition, pin1, pin2, n]
        assert "==" in cond[1]         # condition contains ==
        assert cond[2] == "A"
        assert cond[3] == "ZN"

    def test_width_format(self, sdf):
        widths = [e for e in sdf.cells["INV_X1"] if e[0] == "WIDTH"]
        assert len(widths) == 2
        edges = {w[2] for w in widths}
        assert edges == {"posedge", "negedge"}


# ---------------------------------------------------------------------------
# AND2_X1 — CONDELSE
# ---------------------------------------------------------------------------

class TestAND2:
    def test_condelse_present(self, sdf):
        keywords = [e[0] for e in sdf.cells["AND2_X1"]]
        assert "CONDELSE" in keywords

    def test_condelse_format(self, sdf):
        ce = next(e for e in sdf.cells["AND2_X1"] if e[0] == "CONDELSE")
        # [CONDELSE, pin_1, pin_2, n]
        assert len(ce) == 4
        assert ce[1] == "A1"
        assert ce[2] == "Z"


# ---------------------------------------------------------------------------
# DFFS_X2 — SETUPHOLD and RECREM
# ---------------------------------------------------------------------------

class TestDFFS:
    def test_setuphold_count(self, sdf):
        sh = [e for e in sdf.cells["DFFS_X2"] if e[0] == "SETUPHOLD"]
        assert len(sh) == 2

    def test_setuphold_format(self, sdf):
        sh = next(e for e in sdf.cells["DFFS_X2"] if e[0] == "SETUPHOLD")
        # [SETUPHOLD, cond1, edge1, port1, cond2, edge2, port2, n]
        assert len(sh) == 8
        assert sh[2] in ("posedge", "negedge")
        assert sh[5] in ("posedge", "negedge")

    def test_recrem_format(self, sdf):
        rr = next(e for e in sdf.cells["DFFS_X2"] if e[0] == "RECREM")
        assert len(rr) == 8
        assert rr[3] == "SN"
        assert rr[6] == "CK"


# ---------------------------------------------------------------------------
# MUX2_X1 — conditional SETUPHOLD
# ---------------------------------------------------------------------------

class TestMUX2:
    def test_cond_iopath(self, sdf):
        conds = [e for e in sdf.cells["MUX2_X1"] if e[0] == "COND"]
        assert len(conds) == 2
        assert {c[1] for c in conds} == {"S==1'b0", "S==1'b1"}

    def test_setuphold(self, sdf):
        sh = [e for e in sdf.cells["MUX2_X1"] if e[0] == "SETUPHOLD"]
        assert len(sh) == 2
        # Both port_defs are unconditional here
        for entry in sh:
            assert entry[2] == "posedge"   # edge_1
            assert entry[5] == "posedge"   # edge_2

    def test_recrem(self, sdf):
        rr = [e for e in sdf.cells["MUX2_X1"] if e[0] == "RECREM"]
        assert len(rr) == 1
        assert rr[0][3] == "SN"
        assert rr[0][6] == "CK"


# ---------------------------------------------------------------------------
# Single-cell extraction
# ---------------------------------------------------------------------------

class TestSingleCell:
    def test_only_requested_cell_returned(self):
        sdf = SDFParser().read(SAMPLE_SDF, given_cell="INV_X1")
        assert list(sdf.cells.keys()) == ["INV_X1"]

    def test_case_insensitive(self):
        sdf = SDFParser().read(SAMPLE_SDF, given_cell="inv_x1")
        assert "INV_X1" in sdf.cells

    def test_missing_cell_returns_empty(self, capsys):
        sdf = SDFParser().read(SAMPLE_SDF, given_cell="NONEXISTENT")
        assert "NONEXISTENT" not in sdf.cells
        captured = capsys.readouterr()
        assert "not found" in captured.out


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_no_path_raises(self):
        with pytest.raises(ValueError, match="not provided"):
            SDFParser().read()

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            SDFParser().read("/nonexistent/path/file.sdf")


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_state(self):
        parser = SDFParser()
        parser.read(SAMPLE_SDF)
        assert parser.sdf is not None

        parser.reset()
        assert parser.sdf is None
        assert parser.cell is None

    def test_reuse_after_reset(self):
        parser = SDFParser()
        sdf_a = parser.read(SAMPLE_SDF)

        parser.reset()
        sdf_b = parser.read(SAMPLE_SDF)

        assert sdf_a.cells.keys() == sdf_b.cells.keys()


# ---------------------------------------------------------------------------
# format_entries utility
# ---------------------------------------------------------------------------

class TestFormatEntries:
    def test_output_is_string(self, sdf):
        result = format_entries(sdf.cells["INV_X1"])
        assert isinstance(result, str)

    def test_one_line_per_entry(self, sdf):
        entries = sdf.cells["INV_X1"]
        lines = format_entries(entries).splitlines()
        assert len(lines) == len(entries)
