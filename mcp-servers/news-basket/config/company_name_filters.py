"""
Company name normalization filters.
Add suffixes/prefixes here as new edge cases are discovered.
"""

# Suffixes to strip from company names (order matters - longer first)
COMPANY_SUFFIXES = [
    " Corporation",
    " Incorporated",
    " Technologies",
    " International",
    " Platforms",
    " Holdings",
    " Company",
    " Limited",
    " Group",
    " Inc.",
    " Inc",
    " Ltd.",
    " Ltd",
    " LLC",
    " L.P.",
    " Co.",
    " PLC",
    " N.V.",
    " S.A.",
    " AG",
]

# Prefixes to strip (if any)
COMPANY_PREFIXES = [
    "The ",
]


def clean_company_name(name: str) -> str:
    """
    Remove common corporate suffixes/prefixes for better search matching.
    e.g., "NVIDIA Corporation" -> "NVIDIA"
    """
    result = name

    # Strip prefixes
    for prefix in COMPANY_PREFIXES:
        if result.startswith(prefix):
            result = result[len(prefix):]

    # Strip suffixes
    for suffix in COMPANY_SUFFIXES:
        if result.endswith(suffix):
            result = result[:-len(suffix)]

    # Clean punctuation
    result = result.replace(",", "").strip()

    return result
