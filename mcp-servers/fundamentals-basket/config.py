"""
Configuration for Financials-Basket MCP Server

Centralized configuration for timeouts, rate limits, circuit breaker,
and SWOT analysis thresholds.
"""

# =============================================================================
# TIMEOUTS (seconds) - Increased for completeness-first mode
# =============================================================================

# Global timeout for MCP tool execution
TOOL_TIMEOUT = 90.0  # Match mcp_client timeout

# Per-source timeouts (increased for reliability)
SEC_EDGAR_TIMEOUT = 30.0
SEC_EDGAR_DOCUMENT_TIMEOUT = 45.0  # For fetching full 10-K documents
YAHOO_FINANCE_TIMEOUT = 30.0
CIK_LOOKUP_TIMEOUT = 15.0

# =============================================================================
# RATE LIMITING
# =============================================================================

# SEC EDGAR: 10 requests per second (official limit)
SEC_RATE_LIMIT_REQUESTS = 10
SEC_RATE_LIMIT_PERIOD = 1.0  # seconds

# Yahoo Finance: 5 requests per second (conservative)
YAHOO_RATE_LIMIT_REQUESTS = 5
YAHOO_RATE_LIMIT_PERIOD = 1.0

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

# Exponential backoff: 1s, 2s, 4s
RETRY_MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0
RETRY_EXPONENTIAL_BASE = 2

# HTTP status codes that trigger retry
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

# SEC EDGAR circuit breaker
SEC_CB_FAILURE_THRESHOLD = 5  # Open after 5 consecutive failures
SEC_CB_SUCCESS_THRESHOLD = 3  # Close after 3 consecutive successes
SEC_CB_HALF_OPEN_TIMEOUT = 30.0  # seconds

# Yahoo Finance circuit breaker
YAHOO_CB_FAILURE_THRESHOLD = 3
YAHOO_CB_SUCCESS_THRESHOLD = 2
YAHOO_CB_HALF_OPEN_TIMEOUT = 60.0

# =============================================================================
# CACHE TTL (seconds)
# =============================================================================

# CIK mappings rarely change
CIK_CACHE_TTL = 86400  # 24 hours

# Company facts change with filings
FACTS_CACHE_TTL = 3600  # 1 hour

# Company info (name, SIC, etc.)
COMPANY_INFO_CACHE_TTL = 86400  # 24 hours

# =============================================================================
# SWOT ANALYSIS THRESHOLDS
# =============================================================================

# Revenue growth (3-year CAGR)
REVENUE_GROWTH_STRONG = 15.0  # > 15% = strength
REVENUE_GROWTH_POSITIVE = 5.0  # > 5% = positive
REVENUE_GROWTH_DECLINING = 0.0  # < 0% = weakness

# Net margin
NET_MARGIN_HIGH = 15.0  # > 15% = strength (high profitability)
NET_MARGIN_HEALTHY = 5.0  # > 5% = healthy
NET_MARGIN_THIN = 5.0  # < 5% = thin margins (weakness)
NET_MARGIN_UNPROFITABLE = 0.0  # < 0% = unprofitable (weakness)

# Operating margin
OPERATING_MARGIN_STRONG = 20.0  # > 20% = strong efficiency

# Debt to equity
DEBT_TO_EQUITY_HIGH = 2.0  # > 2.0 = threat (high leverage)
DEBT_TO_EQUITY_ELEVATED = 1.0  # > 1.0 = weakness (elevated debt)
DEBT_TO_EQUITY_LOW = 0.5  # < 0.5 = strength (low leverage)

# R&D as percentage of revenue
RD_HIGH_INVESTMENT = 10.0  # > 10% = opportunity (high R&D investment)

# =============================================================================
# API ENDPOINTS
# =============================================================================

# SEC EDGAR
SEC_BASE_URL = "https://data.sec.gov"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Required headers for SEC EDGAR
SEC_HEADERS = {
    "User-Agent": "AI-Strategy-Copilot/1.0 (contact@example.com)",
    "Accept": "application/json",
}

# Yahoo Finance headers
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

# =============================================================================
# THREAD POOL (for blocking libraries like yfinance)
# =============================================================================

YFINANCE_THREAD_POOL_SIZE = 3
YFINANCE_SEMAPHORE_LIMIT = 3

# =============================================================================
# HTTP SERVER CONFIGURATION (for load-balanced deployment)
# =============================================================================

import os

# HTTP Server
HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "8001"))

# Load Balancer
NGINX_PORT = 8080
INSTANCE_PORTS = [8001, 8002, 8003]

# Instance identification
INSTANCE_ID = os.getenv("INSTANCE_ID", f"financials-default")

# =============================================================================
# INDUSTRY CLASSIFICATION (SIC Code Mapping)
# =============================================================================

# Specific 4-digit SIC codes that need special handling
SIC_SPECIFIC_MAP = {
    "6798": "REAL_ESTATE",   # Real Estate Investment Trusts (REITs)
}

# First 2 digits of SIC → Sector
SIC_SECTOR_MAP = {
    # Financials
    "60": "BANKS",           # Depository Institutions
    "61": "BANKS",           # Non-depository Credit
    "62": "FINANCIALS",      # Securities & Commodities
    "63": "INSURANCE",       # Insurance Carriers
    "64": "INSURANCE",       # Insurance Agents
    "65": "REAL_ESTATE",     # Real Estate
    "67": "FINANCIALS",      # Holding & Investment (except 6798 REITs)

    # Energy
    "10": "MINING",
    "12": "MINING",
    "13": "OIL_GAS",         # Oil & Gas Extraction
    "29": "OIL_GAS",         # Petroleum Refining
    "49": "UTILITIES",       # Electric, Gas, Sanitary

    # Technology
    "35": "TECHNOLOGY",      # Industrial Machinery (computers)
    "36": "TECHNOLOGY",      # Electronic Equipment
    "38": "TECHNOLOGY",      # Instruments
    "73": "TECHNOLOGY",      # Business Services (software)

    # Healthcare
    "28": "HEALTHCARE",      # Chemicals (pharma)
    "80": "HEALTHCARE",      # Health Services

    # Consumer
    "52": "RETAIL",          # Building Materials Retail
    "53": "RETAIL",          # General Merchandise
    "54": "RETAIL",          # Food Stores
    "56": "RETAIL",          # Apparel
    "57": "RETAIL",          # Furniture
    "58": "RETAIL",          # Eating Places
    "59": "RETAIL",          # Misc Retail (incl. e-commerce)

    # Industrials
    "37": "INDUSTRIALS",     # Transportation Equipment
    "40": "TRANSPORTATION",  # Railroad
    "42": "TRANSPORTATION",  # Trucking
    "44": "TRANSPORTATION",  # Water Transport
    "45": "TRANSPORTATION",  # Air Transport

    # Materials
    "14": "MATERIALS",       # Mining (non-metallic)
    "24": "MATERIALS",       # Lumber
    "26": "MATERIALS",       # Paper
    "32": "MATERIALS",       # Stone, Clay, Glass
    "33": "MATERIALS",       # Primary Metals
}


def get_sector_from_sic(sic_code: str) -> str:
    """Get sector classification from SIC code.

    Checks 4-digit specific codes first (e.g., 6798 for REITs),
    then falls back to 2-digit prefix mapping.
    """
    if not sic_code:
        return "GENERAL"
    sic_str = str(sic_code)

    # Check 4-digit specific codes first
    if sic_str in SIC_SPECIFIC_MAP:
        return SIC_SPECIFIC_MAP[sic_str]

    # Fall back to 2-digit prefix
    prefix = sic_str[:2]
    return SIC_SECTOR_MAP.get(prefix, "GENERAL")


# =============================================================================
# INDUSTRY-SPECIFIC XBRL CONCEPTS
# =============================================================================

# Insurance (SIC 63xx, 64xx)
INSURANCE_CONCEPTS = {
    "premiums_earned": ["PremiumsEarnedNet", "PremiumsWrittenNet", "PremiumsEarned"],
    "claims_incurred": ["PolicyholderBenefitsAndClaimsIncurredNet", "BenefitsLossesAndExpenses",
                        "PolicyholderBenefitsAndClaimsIncurredGross"],
    "underwriting_income": ["UnderwritingIncomeLoss", "UnderwritingResultsPropertyCasualtyInsurance"],
    "investment_income": ["NetInvestmentIncome", "InvestmentIncomeNet", "InvestmentIncomeInterestAndDividend"],
    "loss_ratio": ["LossRatio", "InsuranceLossRatio"],
    "policy_acquisition_costs": ["PolicyAcquisitionCosts", "DeferredPolicyAcquisitionCosts"],
}

# Banks (SIC 60xx, 61xx)
BANK_CONCEPTS = {
    "net_interest_income": ["InterestIncomeExpenseNet", "NetInterestIncome",
                            "InterestIncomeExpenseAfterProvisionForLoanLoss"],
    "provision_credit_losses": ["ProvisionForLoanLeaseAndOtherLosses", "ProvisionForCreditLosses",
                                "ProvisionForLoanAndLeaseLosses"],
    "noninterest_income": ["NoninterestIncome"],
    "noninterest_expense": ["NoninterestExpense"],
    "net_loans": ["LoansAndLeasesReceivableNetReportedAmount", "LoansReceivableNet",
                  "LoansAndLeasesReceivableNetOfDeferredIncome"],
    "deposits": ["Deposits", "DepositsDomestic"],
    "tier1_capital_ratio": ["TierOneRiskBasedCapitalRatio", "CommonEquityTier1CapitalRatio"],
    "net_charge_offs": ["AllowanceForLoanAndLeaseLossesWriteoffsNet", "ChargeOffsNet"],
}

# REITs (SIC 65xx, 67xx)
REIT_CONCEPTS = {
    "rental_revenue": ["OperatingLeaseLeaseIncome", "RentalRevenue", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "noi": ["NetOperatingIncome", "OperatingIncomeLoss"],
    "ffo": ["FundsFromOperations", "FundsFromOperationsPerShare"],
    "property_operating_expenses": ["CostOfPropertyRepairsAndMaintenance", "RealEstateTaxExpense"],
    "occupancy_rate": ["OccupancyRate"],
    "same_store_noi": ["SameStoreNetOperatingIncome"],
}

# Energy - Oil & Gas (SIC 13xx, 29xx)
ENERGY_OG_CONCEPTS = {
    "oil_gas_revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                        "OilAndGasRevenue", "SalesRevenueNet"],
    "production_expense": ["ProductionCosts", "LeaseOperatingExpense", "OilAndGasProductionExpense"],
    "depletion": ["DepletionOfOilAndGasProperties", "DepreciationDepletionAndAmortization"],
    "proved_reserves": ["ProvedDevelopedAndUndevelopedReserves", "ProvedReservesOil", "ProvedReservesGas"],
    "exploration_expense": ["ExplorationExpense", "ExplorationCosts"],
    "impairment": ["ImpairmentOfOilAndGasProperties", "AssetImpairmentCharges"],
}

# Utilities (SIC 49xx)
UTILITY_CONCEPTS = {
    "electric_revenue": ["ElectricUtilityRevenue", "RegulatedElectricRevenue", "ElectricDomesticRevenue"],
    "gas_revenue": ["GasUtilityRevenue", "RegulatedGasRevenue", "GasDomesticRevenue"],
    "fuel_cost": ["FuelCosts", "CostOfFuel", "FuelExpense"],
    "purchased_power_cost": ["CostOfPurchasedPower", "PurchasedPowerCost"],
    "regulatory_assets": ["RegulatoryAssets"],
    "regulatory_liabilities": ["RegulatoryLiabilities"],
    "rate_base": ["UtilityPlantNet", "ElectricUtilityPlantNet"],
}

# Technology (SIC 35xx, 36xx, 38xx, 73xx)
TECHNOLOGY_CONCEPTS = {
    "rd_expense": ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"],
    "deferred_revenue": ["DeferredRevenue", "ContractWithCustomerLiability", "DeferredRevenueNoncurrent"],
    "subscription_revenue": ["SubscriptionRevenue", "SaaSRevenue", "RecurringRevenue"],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfServices"],
    "stock_compensation": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
    "intangible_assets": ["IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet"],
    "goodwill": ["Goodwill"],
    "acquired_ip": ["BusinessCombinationRecognizedIdentifiableAssetsAcquiredAndLiabilitiesAssumedIntangibleAssetsOtherThanGoodwill"],
}

# Healthcare / Pharmaceuticals (SIC 28xx, 80xx)
HEALTHCARE_CONCEPTS = {
    "rd_expense": ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold"],
    "selling_general_admin": ["SellingGeneralAndAdministrativeExpense", "GeneralAndAdministrativeExpense"],
    "acquired_iprd": ["ResearchAndDevelopmentInProcess", "AcquiredInProcessResearchAndDevelopment"],
    "milestone_payments": ["CollaborativeArrangementMilestonePayments", "LicenseAndCollaborationRevenue"],
    "inventory": ["InventoryNet", "InventoryFinishedGoodsNetOfReserves"],
    "product_revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "ProductSalesRevenue"],
    "license_revenue": ["LicenseRevenue", "RoyaltyRevenue", "LicenseAndServicesRevenue"],
}

# Retail (SIC 52xx-59xx)
RETAIL_CONCEPTS = {
    "cost_of_goods_sold": ["CostOfGoodsSold", "CostOfGoodsAndServicesSold", "CostOfRevenue"],
    "inventory": ["InventoryNet", "RetailRelatedInventoryMerchandise"],
    "selling_general_admin": ["SellingGeneralAndAdministrativeExpense"],
    "store_count": ["NumberOfStores", "NumberOfRestaurants"],
    "depreciation": ["DepreciationAndAmortization", "Depreciation"],
    "lease_expense": ["OperatingLeaseExpense", "OperatingLeaseCost", "LeaseAndRentalExpense"],
    "same_store_sales": ["SameStoreSales", "ComparableStoreSalesGrowth"],
    "ecommerce_revenue": ["OnlineRevenue", "DigitalRevenue", "ECommerceRevenue"],
}

# Financials - Non-Bank (SIC 62xx, 67xx - Securities, Asset Management)
FINANCIALS_CONCEPTS = {
    "advisory_fees": ["InvestmentAdvisoryFees", "AssetManagementFees", "AdvisoryFees"],
    "assets_under_management": ["AssetsUnderManagement", "ClientAssetsUnderManagement"],
    "trading_revenue": ["PrincipalTransactionsRevenue", "TradingRevenue", "GainLossOnInvestments"],
    "commission_revenue": ["CommissionsAndFees", "BrokerageCommissionsRevenue"],
    "compensation_expense": ["LaborAndRelatedExpense", "CompensationAndBenefitsExpense", "EmployeeBenefitsAndShareBasedCompensation"],
    "investment_income": ["InvestmentIncomeNet", "NetInvestmentIncome"],
    "performance_fees": ["IncentiveFeeRevenue", "PerformanceBasedFees"],
    "fund_expenses": ["FundExpenses", "InvestmentCompanyGeneralPartnerAdvisoryService"],
}

# Industrials / Manufacturing (SIC 37xx)
INDUSTRIALS_CONCEPTS = {
    "cost_of_goods_sold": ["CostOfGoodsSold", "CostOfGoodsAndServicesSold"],
    "inventory": ["InventoryNet", "InventoryRawMaterialsAndSupplies", "InventoryWorkInProcess", "InventoryFinishedGoods"],
    "depreciation": ["DepreciationAndAmortization", "Depreciation"],
    "backlog": ["Backlog", "UnfilledOrders", "OrderBacklog"],
    "capital_expenditure": ["PaymentsToAcquirePropertyPlantAndEquipment", "CapitalExpendituresIncurredButNotYetPaid"],
    "property_plant_equipment": ["PropertyPlantAndEquipmentNet", "PropertyPlantAndEquipmentGross"],
    "pension_expense": ["DefinedBenefitPlanNetPeriodicBenefitCost", "PensionAndOtherPostretirementBenefitExpense"],
    "warranty_expense": ["ProductWarrantyExpense", "StandardProductWarrantyAccrual"],
}

# Transportation (SIC 40xx-45xx)
TRANSPORTATION_CONCEPTS = {
    "operating_revenue": ["OperatingRevenue", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "fuel_expense": ["AircraftFuelExpense", "FuelCosts", "FuelExpense"],
    "labor_expense": ["SalariesWagesAndBenefits", "LaborAndRelatedExpense"],
    "depreciation": ["DepreciationAndAmortization", "Depreciation"],
    "maintenance_expense": ["AircraftMaintenanceMaterialsAndRepairs", "MaintenanceAndRepairsExpense"],
    "revenue_passenger_miles": ["RevenuePassengerMiles", "PassengerRevenueMiles"],
    "available_seat_miles": ["AvailableSeatMiles", "AvailableSeatMilesASMs"],
    "load_factor": ["PassengerLoadFactor", "LoadFactor"],
    "fleet_size": ["NumberOfAircraft", "FleetSize"],
}

# Materials (SIC 14xx, 24xx, 26xx, 32xx, 33xx)
MATERIALS_CONCEPTS = {
    "cost_of_goods_sold": ["CostOfGoodsSold", "CostOfGoodsAndServicesSold"],
    "inventory": ["InventoryNet", "InventoryRawMaterialsAndSupplies"],
    "depreciation": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"],
    "energy_costs": ["UtilitiesExpense", "EnergyCosts", "NaturalGasPurchases"],
    "environmental_liabilities": ["AccruedEnvironmentalLossContingencies", "EnvironmentalLossContingencyStatementOfFinancialPositionExtensibleListNotDisclosed"],
    "property_plant_equipment": ["PropertyPlantAndEquipmentNet"],
    "capital_expenditure": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "raw_materials": ["InventoryRawMaterialsAndSupplies", "RawMaterials"],
}

# Mining (SIC 10xx, 12xx)
MINING_CONCEPTS = {
    "mining_revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "MiningRevenue", "Revenues"],
    "cost_of_production": ["CostOfGoodsSold", "ProductionCosts", "MiningCosts"],
    "depletion": ["DepletionOfMinesAndMineralDeposits", "DepreciationDepletionAndAmortization"],
    "exploration_expense": ["ExplorationExpense", "MineralExplorationCosts", "ExplorationCosts"],
    "reclamation_liabilities": ["AssetRetirementObligation", "MineReclamationAndClosingLiability"],
    "mineral_reserves": ["ProvedAndProbableMineralReserves", "MineralReserves"],
    "depreciation": ["DepreciationAndAmortization"],
    "royalty_expense": ["RoyaltyExpense", "MiningRoyalties"],
}

# Map sector to concept dictionary
INDUSTRY_CONCEPTS = {
    "INSURANCE": INSURANCE_CONCEPTS,
    "BANKS": BANK_CONCEPTS,
    "REAL_ESTATE": REIT_CONCEPTS,
    "OIL_GAS": ENERGY_OG_CONCEPTS,
    "UTILITIES": UTILITY_CONCEPTS,
    "TECHNOLOGY": TECHNOLOGY_CONCEPTS,
    "HEALTHCARE": HEALTHCARE_CONCEPTS,
    "RETAIL": RETAIL_CONCEPTS,
    "FINANCIALS": FINANCIALS_CONCEPTS,
    "INDUSTRIALS": INDUSTRIALS_CONCEPTS,
    "TRANSPORTATION": TRANSPORTATION_CONCEPTS,
    "MATERIALS": MATERIALS_CONCEPTS,
    "MINING": MINING_CONCEPTS,
}
