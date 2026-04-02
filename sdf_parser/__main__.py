"""CLI entry point: python -m sdf_parser  or  sdf-parser (installed script)."""

import argparse
import sys

from .parser import SDFParser
from .utils import format_entries


def main():
    parser = argparse.ArgumentParser(
        prog="sdf-parser",
        description="Parse an SDF file and print timing data.",
        epilog=(
            "Examples:\n"
            "  sdf-parser timing.sdf\n"
            "  sdf-parser timing.sdf --cell INV_X1\n"
            "  sdf-parser sdf_corners/ --header\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", help="Path to an .sdf file or directory of .sdf files")
    parser.add_argument(
        "--cell", "-c",
        metavar="CELLNAME",
        help="Print only this cell (case-insensitive)",
    )
    parser.add_argument(
        "--header",
        action="store_true",
        help="Print header fields (SDFVERSION, DESIGN, TIMESCALE, …)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print package version and exit",
    )
    args = parser.parse_args()

    if args.version:
        from sdf_parser import __version__
        print(__version__)
        return

    sdf_parser = SDFParser()
    sdf = sdf_parser.read(args.path, given_cell=args.cell)

    if sdf is None:
        sys.exit(1)

    if args.header:
        print("=== Header ===")
        for k, v in sdf.header_data.items():
            print(f"  {k}: {v}")
        print()

    if args.cell:
        cell_key = next(
            (k for k in sdf.cells if k.lower() == args.cell.lower()), None
        )
        if cell_key:
            print(f"=== {cell_key} ===")
            print(format_entries(sdf.cells[cell_key]))
        else:
            print(f"Cell '{args.cell}' not found.")
            sys.exit(1)
    else:
        for cell_name, entries in sdf.cells.items():
            print(f"=== {cell_name} ({len(entries)} entries) ===")
            print(format_entries(entries))
            print()


if __name__ == "__main__":
    main()
