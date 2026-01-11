#!/usr/bin/env python3
"""
Fetch raw macro economic data from BEA, BLS, and FRED.
Outputs the data schema with actual values.
"""

import asyncio
import json
import sys
sys.path.insert(0, '/home/vn6295337/Researcher-Agent')

from mcp_client import call_mcp_server


async def fetch_macro():
    """Fetch macro data from multiple sources."""
    result = await call_mcp_server(
        'macro-basket',
        'get_all_sources_macro',
        {},
        timeout=90
    )
    return result


def print_metric(key, val, indent=2):
    """Print a metric with proper indentation."""
    prefix = " " * indent
    print(f"\n{prefix}{key}")
    if isinstance(val, dict):
        for k, v in val.items():
            print(f"{prefix}  {k}: {v}")
    elif val is None:
        print(f"{prefix}  value: null")
    else:
        print(f"{prefix}  value: {val}")


def print_schema(data: dict):
    """Print data schema in plain text format."""
    print("Macro Economic Data Schema")
    print("=" * 50)

    # BEA + BLS
    if 'bea_bls' in data:
        src = data['bea_bls']
        print(f"\n\nBEA + BLS (Primary)")
        print("-" * 40)
        print(f"source: {src.get('source')}")
        print(f"as_of: {src.get('as_of')}")
        for key, val in src.get('data', {}).items():
            print_metric(key, val)

    # FRED
    if 'fred' in data:
        src = data['fred']
        print(f"\n\nFRED (Secondary)")
        print("-" * 40)
        print(f"source: {src.get('source')}")
        print(f"as_of: {src.get('as_of')}")
        for key, val in src.get('data', {}).items():
            print_metric(key, val)

    # Source hierarchy
    if 'primary_source_hierarchy' in data:
        print(f"\n\nPrimary Source Hierarchy")
        print("-" * 40)
        for key, val in data['primary_source_hierarchy'].items():
            print(f"{key}: {val}")


async def main():
    print("Fetching macro economic data...")
    data = await fetch_macro()

    if data:
        print_schema(data)

        with open('/home/vn6295337/Researcher-Agent/docs/macro_raw.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nRaw JSON saved to: docs/macro_raw.json")
    else:
        print("Failed to fetch data")


if __name__ == '__main__':
    asyncio.run(main())
