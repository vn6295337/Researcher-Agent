"""
Company Sampler - Random selection of tickers for MCP stress testing.

Supports multiple sampling strategies:
- Uniform random
- Stratified by sector
- Market cap weighted (simulated)
- Edge case focused
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional
from enum import Enum
from dataclasses import dataclass


class SamplingStrategy(Enum):
    UNIFORM = "uniform"
    STRATIFIED = "stratified"
    EDGE_CASE = "edge_case"
    MIXED = "mixed"


@dataclass
class Company:
    ticker: str
    name: str
    sector: str
    note: Optional[str] = None


class CompanySampler:
    """Samples companies for MCP stress testing with configurable strategies."""

    def __init__(self, fixture_path: Optional[Path] = None):
        """Initialize sampler with ticker fixture data.

        Args:
            fixture_path: Path to test_tickers.json. If None, uses default location.
        """
        if fixture_path is None:
            fixture_path = Path(__file__).parent.parent / "fixtures" / "test_tickers.json"

        with open(fixture_path) as f:
            data = json.load(f)

        self.companies = [
            Company(**c) for c in data.get("sp500_sample", [])
        ]
        self.edge_cases = [
            Company(**c) for c in data.get("edge_cases", [])
        ]
        self.sectors = data.get("sectors", [])
        self._by_sector: Dict[str, List[Company]] = {}
        self._build_sector_index()

    def _build_sector_index(self):
        """Build index of companies by sector for stratified sampling."""
        for company in self.companies:
            if company.sector not in self._by_sector:
                self._by_sector[company.sector] = []
            self._by_sector[company.sector].append(company)

    def sample(
        self,
        n: int,
        strategy: SamplingStrategy = SamplingStrategy.UNIFORM,
        seed: Optional[int] = None
    ) -> List[Company]:
        """Sample n companies using the specified strategy.

        Args:
            n: Number of companies to sample
            strategy: Sampling strategy to use
            seed: Random seed for reproducibility

        Returns:
            List of sampled Company objects
        """
        if seed is not None:
            random.seed(seed)

        if strategy == SamplingStrategy.UNIFORM:
            return self._sample_uniform(n)
        elif strategy == SamplingStrategy.STRATIFIED:
            return self._sample_stratified(n)
        elif strategy == SamplingStrategy.EDGE_CASE:
            return self._sample_edge_case(n)
        elif strategy == SamplingStrategy.MIXED:
            return self._sample_mixed(n)
        else:
            raise ValueError(f"Unknown sampling strategy: {strategy}")

    def _sample_uniform(self, n: int) -> List[Company]:
        """Uniform random sampling from all companies."""
        pool = self.companies.copy()
        n = min(n, len(pool))
        return random.sample(pool, n)

    def _sample_stratified(self, n: int) -> List[Company]:
        """Stratified sampling - equal representation from each sector."""
        result = []
        sectors = list(self._by_sector.keys())
        per_sector = max(1, n // len(sectors))

        for sector in sectors:
            sector_companies = self._by_sector.get(sector, [])
            sample_size = min(per_sector, len(sector_companies))
            result.extend(random.sample(sector_companies, sample_size))

        # Fill remaining with random samples if needed
        if len(result) < n:
            remaining = [c for c in self.companies if c not in result]
            extra = min(n - len(result), len(remaining))
            result.extend(random.sample(remaining, extra))

        return result[:n]

    def _sample_edge_case(self, n: int) -> List[Company]:
        """Sample primarily from edge cases, fill with normal if needed."""
        result = []

        # Start with all edge cases
        edge_sample_size = min(n, len(self.edge_cases))
        result.extend(random.sample(self.edge_cases, edge_sample_size))

        # Fill remaining with normal companies
        if len(result) < n:
            remaining = n - len(result)
            result.extend(random.sample(self.companies, remaining))

        return result[:n]

    def _sample_mixed(self, n: int) -> List[Company]:
        """Mixed strategy: 70% uniform, 20% stratified boost, 10% edge cases."""
        result = []

        # 10% edge cases
        edge_n = max(1, n // 10)
        edge_sample = min(edge_n, len(self.edge_cases))
        result.extend(random.sample(self.edge_cases, edge_sample))

        # 90% from main pool (with some stratification)
        remaining = n - len(result)
        main_sample = self._sample_uniform(remaining)
        result.extend(main_sample)

        random.shuffle(result)
        return result[:n]

    def get_all_tickers(self) -> List[str]:
        """Get all available tickers."""
        return [c.ticker for c in self.companies + self.edge_cases]

    def get_sectors(self) -> List[str]:
        """Get list of available sectors."""
        return self.sectors.copy()

    def get_by_sector(self, sector: str) -> List[Company]:
        """Get all companies in a specific sector."""
        return self._by_sector.get(sector, []).copy()


def create_test_batch(
    batch_size: int = 20,
    strategy: str = "uniform",
    seed: Optional[int] = None
) -> List[Dict]:
    """Convenience function to create a test batch.

    Args:
        batch_size: Number of companies in batch
        strategy: "uniform", "stratified", "edge_case", or "mixed"
        seed: Random seed for reproducibility

    Returns:
        List of dicts with ticker and name
    """
    sampler = CompanySampler()
    strategy_enum = SamplingStrategy(strategy)
    companies = sampler.sample(batch_size, strategy_enum, seed)
    return [{"ticker": c.ticker, "name": c.name, "sector": c.sector} for c in companies]


if __name__ == "__main__":
    # Demo usage
    sampler = CompanySampler()
    print("=== Uniform Sample (10) ===")
    for c in sampler.sample(10, SamplingStrategy.UNIFORM, seed=42):
        print(f"  {c.ticker}: {c.name} ({c.sector})")

    print("\n=== Stratified Sample (10) ===")
    for c in sampler.sample(10, SamplingStrategy.STRATIFIED, seed=42):
        print(f"  {c.ticker}: {c.name} ({c.sector})")

    print("\n=== Edge Case Sample (5) ===")
    for c in sampler.sample(5, SamplingStrategy.EDGE_CASE, seed=42):
        print(f"  {c.ticker}: {c.name} ({c.sector})")
