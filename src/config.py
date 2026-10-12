"""
Configuration and constants for the Groww Multi-Agent System.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Robust data path resolution (handles both 'Data' and 'data')
DATA_DIR = BASE_DIR / "Data"
if not DATA_DIR.exists():
    DATA_DIR = BASE_DIR / "data"

PARSED_DIR = DATA_DIR / "parsed"
SCHEMES_MANIFEST_PATH = PARSED_DIR / "parse_manifest.json"

NORMALIZED_REVIEWS_PATH = DATA_DIR / "normalized_reviews.json"
if not NORMALIZED_REVIEWS_PATH.exists():
    NORMALIZED_REVIEWS_PATH = PARSED_DIR / "normalized_reviews.json"

ANALYZED_THEMES_PATH = BASE_DIR / "analyzed_themes.json"
if not ANALYZED_THEMES_PATH.exists():
    ANALYZED_THEMES_PATH = DATA_DIR / "analyzed_themes.json"

# Closed Set of Schemes (5 schemes from Milestone 1)
VALID_SCHEME_IDS = [
    "large_cap",
    "mid_cap",
    "small_cap",
    "gold_fof",
    "silver_fof"
]

# Canonical scheme names mapping
SCHEME_NAMES = {
    "large_cap": "HDFC Large Cap Fund Direct Growth",
    "mid_cap": "HDFC Mid Cap Fund Direct Growth",
    "small_cap": "HDFC Small Cap Fund Direct Growth",
    "gold_fof": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
    "silver_fof": "HDFC Silver ETF FoF Direct Growth"
}

# Closed Set of Scheme Sections (7 Text Blocks per scheme file)
VALID_SECTIONS = [
    "Key fund facts",
    "Exit load",
    "Benchmark",
    "Investment objective",
    "Stamp duty and tax",
    "Fund management",
    "Minimum investments"
]

# Closed Set of Themes from Milestone 2
VALID_THEME_IDS = [
    "other",
    "trading_charts",
    "money_movement",
    "reliability",
    "fees_brokerage"
]

# Canonical NAV Date across all 5 scheme files
CANONICAL_NAV_DATE = "25-Jun-2026"

# Review Dataset Time Window
REVIEW_WINDOW = "2026-04-12 to 2026-07-04"

# Execution Budget Invariants
MAX_REWORK_ATTEMPTS = 1
MAX_REFINEMENT_ATTEMPTS = 5
MAX_REPLY_SENTENCES = 3
