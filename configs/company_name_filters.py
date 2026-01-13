"""
Company name normalization filters.
Add suffixes/prefixes here as new edge cases are discovered.
"""

# Suffixes to strip from company names (order matters - longer first)
COMPANY_SUFFIXES = [
    " - Common Stock",
    " - Class A Common Stock",
    " - Class B Common Stock",
    " - Class C Common Stock",
    " - Ordinary Shares",
    " - American Depositary Shares",
    " Corporation",
    " Incorporated",
    " Technologies",
    " Technology",
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
    " Corp.",
    " Corp",
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
         "Meta Platforms, Inc." -> "Meta"
    """
    result = name

    # Strip prefixes
    for prefix in COMPANY_PREFIXES:
        if result.startswith(prefix):
            result = result[len(prefix):]

    # Clean punctuation first (commas interfere with suffix matching)
    result = result.replace(",", "").strip()

    # Strip suffixes iteratively (handles "Meta Platforms Inc" -> "Meta")
    changed = True
    while changed:
        changed = False
        for suffix in COMPANY_SUFFIXES:
            if result.endswith(suffix):
                result = result[: -len(suffix)].strip()
                changed = True
                break

    return result
