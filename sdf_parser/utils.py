"""Utility helpers for sdf_parser."""

try:
    from termcolor import colored
except ImportError:
    def colored(text, color=None, **kwargs):  # type: ignore[misc]
        return text


def format_entries(cell: list) -> str:
    """Format a list of parsed timing entries as a human-readable string.

    Args:
        cell: List of parsed timing entry lists, as returned in ``SDF.cells``.

    Returns:
        One entry per line, fields separated by spaces.
    """
    return "\n".join(" ".join(str(f) for f in entry) for entry in cell)
