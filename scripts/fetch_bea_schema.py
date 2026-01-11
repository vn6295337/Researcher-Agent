#!/usr/bin/env python3
"""
Fetch raw BEA (Bureau of Economic Analysis) data and output the schema.
Shows raw API response structure for NIPA GDP data.
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import httpx

# Load environment variables
env_paths = [
    Path.home() / ".env",
    Path(__file__).parent.parent / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

BEA_API_KEY = os.getenv("BEA_API_KEY")
BEA_BASE_URL = "https://apps.bea.gov/api/data"


def print_table(title: str, rows: list, col_widths: list = None):
    """Print ASCII table."""
    if not rows:
        return

    # Calculate column widths
    if col_widths is None:
        col_widths = []
        for col in range(len(rows[0])):
            width = max(len(str(row[col])) for row in rows)
            col_widths.append(width)

    # Print header
    print(f"\n{title}")

    # Top border
    line = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    print(line)

    # Header row
    header = rows[0]
    row_str = "│" + "│".join(f" {str(header[i]).ljust(col_widths[i])} " for i in range(len(header))) + "│"
    print(row_str)

    # Separator
    line = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    print(line)

    # Data rows
    for row in rows[1:]:
        row_str = "│" + "│".join(f" {str(row[i]).ljust(col_widths[i])} " for i in range(len(row))) + "│"
        print(row_str)

    # Bottom border
    line = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
    print(line)


async def fetch_gdp_data() -> dict:
    """Fetch GDP data from BEA NIPA dataset."""
    if not BEA_API_KEY:
        return {"error": "BEA_API_KEY not configured"}

    try:
        async with httpx.AsyncClient() as client:
            params = {
                "UserID": BEA_API_KEY,
                "method": "GetData",
                "datasetname": "NIPA",
                "TableName": "T10101",  # Percent Change From Preceding Period in Real GDP
                "Frequency": "Q",        # Quarterly
                "Year": "X",             # All recent years
                "ResultFormat": "JSON"
            }
            response = await client.get(BEA_BASE_URL, params=params, timeout=15)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


async def main():
    print("BEA Data Schema")
    print("=" * 60)
    print()
    print("Endpoint: https://apps.bea.gov/api/data")
    print("Dataset: NIPA (National Income and Product Accounts)")
    print("Table: T10101 (Percent Change From Preceding Period in Real GDP)")
    print()

    if not BEA_API_KEY:
        print("ERROR: BEA_API_KEY not configured")
        print("Add BEA_API_KEY to ~/.env file")
        print("Get free key at: https://apps.bea.gov/api/signup/")
        return

    print("Fetching GDP data...")
    data = await fetch_gdp_data()

    if "error" in data:
        print(f"ERROR: {data}")
        return

    beaapi = data.get("BEAAPI", {})
    results = beaapi.get("Results", {})

    if not results:
        print("ERROR: No results returned")
        return

    print()
    print("=" * 60)
    print()

    # Print raw API response structure
    print("Raw API Response Structure")
    print("-" * 40)

    # Request metadata
    request = beaapi.get("Request", {})
    rows = [["field", "value"]]
    rows.append(["RequestParam.DataSetName", request.get("RequestParam", [{}])[0].get("ParameterValue", "") if request.get("RequestParam") else ""])
    rows.append(["RequestParam.TableName", "T10101"])
    rows.append(["RequestParam.Frequency", "Q"])
    print_table("BEAAPI.Request", rows)

    # Results metadata
    rows = [["field", "description"]]
    rows.append(["Statistic", results.get("Statistic", "")])
    rows.append(["UTCProductionTime", results.get("UTCProductionTime", "")])
    rows.append(["Notes[]", "Array of data notes/descriptions"])
    rows.append(["Data[]", "Array of data observations"])
    print_table("BEAAPI.Results", rows)

    # Data row structure
    data_rows = results.get("Data", [])
    if data_rows:
        # Get a recent GDP row (LineNumber = 1 is Real GDP)
        gdp_rows = [r for r in data_rows if r.get("LineNumber") == "1"]
        gdp_rows.sort(key=lambda x: x.get("TimePeriod", ""), reverse=True)

        if gdp_rows:
            sample = gdp_rows[0]
            rows = [["field", "value"]]
            rows.append(["TableName", sample.get("TableName", "")])
            rows.append(["SeriesCode", sample.get("SeriesCode", "")])
            rows.append(["LineNumber", sample.get("LineNumber", "")])
            rows.append(["LineDescription", sample.get("LineDescription", "")])
            rows.append(["TimePeriod", sample.get("TimePeriod", "")])
            rows.append(["METRIC_NAME", sample.get("METRIC_NAME", "")])
            rows.append(["CL_UNIT", sample.get("CL_UNIT", "")])
            rows.append(["UNIT_MULT", sample.get("UNIT_MULT", "")])
            rows.append(["DataValue", sample.get("DataValue", "")])
            rows.append(["NoteRef", sample.get("NoteRef", "")])
            print_table("Data[0] (Row Structure)", rows)

    # Field descriptions
    print()
    print()
    print("Field Descriptions")
    print("-" * 40)

    rows = [["field", "description"]]
    rows.append(["TableName", "NIPA table identifier (T10101)"])
    rows.append(["SeriesCode", "BEA series code for the metric"])
    rows.append(["LineNumber", "Row number in the table (1 = Real GDP)"])
    rows.append(["LineDescription", "Human-readable metric name"])
    rows.append(["TimePeriod", "Time period (YYYYQN format, e.g., 2025Q3)"])
    rows.append(["METRIC_NAME", "Metric type (e.g., Percent Change)"])
    rows.append(["CL_UNIT", "Classification unit"])
    rows.append(["UNIT_MULT", "Unit multiplier"])
    rows.append(["DataValue", "The actual data value"])
    rows.append(["NoteRef", "Reference to notes array"])
    print_table("Field Descriptions", rows)

    # Recent GDP values
    if gdp_rows:
        print()
        print()
        print("Recent GDP Growth Data")
        print("-" * 40)

        rows = [["TimePeriod", "DataValue", "LineDescription"]]
        for row in gdp_rows[:6]:
            rows.append([
                row.get("TimePeriod", ""),
                row.get("DataValue", ""),
                row.get("LineDescription", "")[:40]
            ])
        print_table("Real GDP % Change (Latest)", rows)

    # Save raw JSON
    output_path = Path(__file__).parent.parent / "docs" / "bea_raw.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nRaw JSON saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
