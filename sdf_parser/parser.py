"""Core SDF parser — SDFParser and SDF classes."""

import os
import re
from copy import deepcopy

from .utils import colored, format_entries


class SDF:
    """Represents a parsed SDF file or a merged collection of SDF files.

    Attributes:
        header_data: Key-value pairs from the SDF header
            (e.g. ``SDFVERSION``, ``DESIGN``, ``TIMESCALE``).
        cells: Maps cell name to a list of parsed timing entries.
            Each entry is a list whose first element is the construct
            keyword; see :class:`SDFParser` for the per-keyword layout.
        files: Paths of all SDF files that were parsed into this object.
    """

    def __init__(self) -> None:
        self.header_data: dict = {}
        self.cells: dict = {}
        self.files: list = []

    def __repr__(self) -> str:
        return (
            f"SDF(cells={len(self.cells)}, "
            f"files={len(self.files)}, "
            f"header={list(self.header_data.keys())})"
        )


class SDFParser:
    """Parser for Standard Delay Format (SDF) files.

    Supports single files and directories of SDF files.  When parsing a
    directory every ``.sdf`` file is merged into a single :class:`SDF`
    object; cells appearing in more than one file are cross-checked and
    a warning is printed on any content mismatch.

    Supported constructs:

    +------------+-------------------------------------------------------+
    | Construct  | Parsed entry format                                   |
    +============+=======================================================+
    | IOPATH     | ``[IOPATH, pin_1, pin_2, n]``                         |
    +------------+-------------------------------------------------------+
    | COND       | ``[COND, condition, pin_1, pin_2, n]``                |
    +------------+-------------------------------------------------------+
    | CONDELSE   | ``[CONDELSE, pin_1, pin_2, n]``                       |
    +------------+-------------------------------------------------------+
    | WIDTH      | ``[WIDTH, condition, edge, port, n]``                 |
    +------------+-------------------------------------------------------+
    | SETUPHOLD  | ``[SETUPHOLD, cond1, edge1, port1,``                  |
    |            |  ``cond2, edge2, port2, n]``                          |
    +------------+-------------------------------------------------------+
    | RECREM     | ``[RECREM, cond1, edge1, port1,``                     |
    |            |  ``cond2, edge2, port2, n]``                          |
    +------------+-------------------------------------------------------+

    ``condition`` fields are ``None`` when no ``COND`` qualifier is present.
    ``n`` is the count of delay value tuples (e.g. 3 for min/typ/max).

    Args:
        path: Default file or directory path used when :meth:`read` is
            called without an explicit ``path`` argument.

    Example::

        from sdf_parser import SDFParser

        parser = SDFParser()
        sdf = parser.read("timing.sdf")

        for entry in sdf.cells["INV_X1"]:
            print(entry)
    """

    def __init__(self, path: str = None) -> None:
        self.sdf: SDF = None
        self.cell: str = None
        self.path: str = path

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear internal state so the parser can be reused for a new file.

        Example::

            parser = SDFParser()
            sdf_fast = parser.read("corner_fast.sdf")

            parser.reset()
            sdf_slow = parser.read("corner_slow.sdf")
        """
        self.sdf = None
        self.cell = None

    def read(self, path: str = None, given_cell: str = None) -> SDF:
        """Parse one SDF file or all SDF files in a directory.

        When *path* points to a directory every ``.sdf`` file found
        directly inside it is parsed.  Cells that appear in more than one
        file are merged; any content mismatch triggers a warning.

        Args:
            path: Path to an ``.sdf`` file or a directory containing
                ``.sdf`` files.  Falls back to the constructor ``path``.
            given_cell: If provided, only this cell is extracted
                (case-insensitive) and parsing stops as soon as it is
                found.

        Returns:
            A populated :class:`SDF` instance.

        Raises:
            ValueError: If no path is provided.
            FileNotFoundError: If *path* does not exist.
            IOError: If a file cannot be opened for reading.
        """
        if not path:
            path = self.path
            if not path:
                raise ValueError("File path not provided.")

        sdf_files = self._collect_files(path)

        finished: list = []
        for filename in sdf_files:
            try:
                sdf_file = open(filename, "r")
            except IOError as exc:
                raise IOError(f"Could not read file: {filename}") from exc

            current_sdf = self._parse_file(sdf_file, given_cell)
            sdf_file.close()

            if given_cell and given_cell not in current_sdf.cells:
                print(colored(
                    f"Warning: Cell '{given_cell}' not found in {filename}",
                    "yellow",
                ))

            if not self.sdf:
                self.sdf = current_sdf
            else:
                self._merge(current_sdf, filename, finished)

            finished.append(filename)

        self.sdf.files = sdf_files
        return self.sdf

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_files(self, path: str) -> list:
        if os.path.isfile(path):
            return [path]
        if os.path.isdir(path):
            files = [
                os.path.join(path, f)
                for f in os.listdir(path)
                if f.endswith(".sdf")
            ]
            if not files:
                print(f"Warning: No SDF files found in {path}")
                return []
            if len(files) == 1:
                print(f"Warning: Only 1 SDF file found in {path}")
            return files
        raise FileNotFoundError(f"Could not find file or directory: {path}")

    def _parse_file(self, sdf_file, given_cell: str) -> SDF:
        current_sdf = SDF()
        self.cell = None
        if given_cell:
            given_cell = given_cell.lower()
        header = not bool(self.sdf)

        line = sdf_file.readline()
        while line:
            next_line = sdf_file.readline()
            line = line.strip()
            if not line:
                line = next_line
                continue

            # Header key-value pairs
            if header and not line.startswith("(CELLTYPE"):
                data = re.fullmatch(r'\((?P<key>.+)\s+"(?P<value>.+)"\)', line)
                if not data:
                    data = re.fullmatch(r'\((?P<key>.+)\s+(?P<value>.+)\)', line)
                if data:
                    current_sdf.header_data[data.group("key")] = data.group("value")

            # New cell declaration
            if line.startswith("(CELLTYPE"):
                if header:
                    header = False
                celltype = line.split(' "')[1][:-2]

                if given_cell and given_cell != celltype.lower():
                    if self.cell:
                        return current_sdf
                    line = next_line
                    continue

                current_sdf.cells[celltype] = []
                self.cell = celltype

            if self.cell:
                delay = self.parse_line(line)
                if delay:
                    current_sdf.cells[self.cell].append(delay)

            line = next_line

        return current_sdf

    def _merge(self, incoming: SDF, filename: str, finished: list) -> None:
        for cell in incoming.cells:
            if cell in self.sdf.cells:
                diff = self._cells_differ(
                    deepcopy(self.sdf.cells[cell]),
                    deepcopy(incoming.cells[cell]),
                )
                if diff:
                    parsed_so_far = "\n".join(
                        os.path.basename(f) for f in finished
                    )
                    detail = (
                        "Number of cell data lines differ."
                        if isinstance(diff, bool)
                        else f"Difference found in data line: {diff}"
                    )
                    msg = (
                        f"Warning: Cell '{cell}' contains different data "
                        f"than previously parsed files.\n{detail}\n\n"
                        f"Conflicting file: {filename}\n\n"
                        f"Files parsed without conflict:\n{parsed_so_far}\n\n"
                        f"Data from conflict-free files (used in result):\n"
                        f"{format_entries(self.sdf.cells[cell])}\n\n"
                        f"Data from conflicting file (excluded):\n"
                        f"{format_entries(incoming.cells[cell])}\n"
                    )
                    print(colored(msg, "yellow"))
            else:
                self.sdf.cells[cell] = incoming.cells[cell]

    # ------------------------------------------------------------------
    # Parsing primitives
    # ------------------------------------------------------------------

    def parse_line(self, line: str) -> list:
        """Parse a single SDF timing or constraint line.

        Args:
            line: A single stripped line from an SDF file.

        Returns:
            A list of parsed fields, or ``None`` if the line does not
            match any supported construct.
        """
        keyword_re = r'\((?P<keyword>\S+)\s+(?P<delay_data>.+)\)'
        match = re.fullmatch(keyword_re, line)
        if not match:
            return None

        output = [match.group("keyword")]
        delay_data = match.group("delay_data")

        cond_re = r'(?P<condition>\S+==\S+)\s+\(\S+\s+(?P<iopath>.+)\)\)'
        iopath_re = r'(?P<pin_1>\S+)\s+(?P<pin_2>\S+)\s+(?P<delayvalues>.+)'
        width_re = r'\((?P<port_def_1>[^:]+)\)\s+(?P<delayvalues>.+)'
        recrem_re = (
            r'\((?P<port_def_1>[^:]+)\)\s+\((?P<port_def_2>[^:]+)\)\s+'
            r'(?P<delayvalues>.+)'
        )
        port_def_re = (
            r'(COND\s+(?P<condition>\S+)\s+\()?(?P<sign>\S+)edge\s+'
            r'(?P<port>[^:\)]+)\)?'
        )

        if output[0] == "CONDELSE":
            inner = re.fullmatch(keyword_re, delay_data)
            if not inner:
                print(f"WARNING: CONDELSE line was not successfully parsed:\n{line}")
                return None
            data = re.fullmatch(iopath_re, inner.group("delay_data"))
            if not data:
                print(f"WARNING: CONDELSE line was not successfully parsed:\n{line}")
                return None
            output.extend([data.group("pin_1"), data.group("pin_2")])

        else:
            data = re.fullmatch(cond_re, delay_data)
            if data:
                iopath = re.fullmatch(iopath_re, data.group("iopath"))
                output.extend([
                    data.group("condition"),
                    iopath.group("pin_1"),
                    iopath.group("pin_2"),
                ])
                data = iopath
            else:
                data = re.fullmatch(recrem_re, delay_data)
                if data:
                    def_1 = re.fullmatch(port_def_re, data.group("port_def_1"))
                    def_2 = re.fullmatch(port_def_re, data.group("port_def_2"))
                    output.extend([
                        def_1.group("condition"),
                        f"{def_1.group('sign')}edge",
                        def_1.group("port"),
                        def_2.group("condition"),
                        f"{def_2.group('sign')}edge",
                        def_2.group("port"),
                    ])
                else:
                    data = re.fullmatch(width_re, delay_data)
                    if data:
                        def_1 = re.fullmatch(port_def_re, data.group("port_def_1"))
                        if def_1:
                            output.extend([
                                def_1.group("condition"),
                                f"{def_1.group('sign')}edge",
                                def_1.group("port"),
                            ])
                        else:
                            return None
                    else:
                        data = re.fullmatch(iopath_re, delay_data)
                        if data:
                            output.extend([
                                data.group("pin_1"),
                                data.group("pin_2"),
                            ])
                        else:
                            return None

        output.append(len(data.group("delayvalues").split(" ")))
        return output

    @staticmethod
    def _cells_differ(cell_1: list, cell_2: list):
        if len(cell_1) != len(cell_2):
            return True
        for line in cell_2:
            if line in cell_1:
                cell_1.remove(line)
            else:
                return line
        return False
