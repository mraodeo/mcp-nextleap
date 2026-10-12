"""
In-memory caching and retrieval of canonical corpora.
Loads and indexes scheme files, review clusters, and normalized complaints.
"""
import json
from typing import Dict, Any, Optional, List
from src.config import (
    PARSED_DIR,
    SCHEMES_MANIFEST_PATH,
    ANALYZED_THEMES_PATH,
    NORMALIZED_REVIEWS_PATH,
    VALID_SCHEME_IDS,
    VALID_SECTIONS,
    SCHEME_NAMES
)

class DataLoader:
    _instance: Optional["DataLoader"] = None

    def __init__(self):
        self.schemes_data: Dict[str, Dict[str, Any]] = {}
        self.scheme_text_blocks: Dict[str, Dict[str, str]] = {}
        self.themes_data: Dict[str, Any] = {}
        self.theme_lookup: Dict[str, Dict[str, Any]] = {}
        self.reviews: List[Dict[str, Any]] = []
        self._load_all()

    @classmethod
    def get_instance(cls) -> "DataLoader":
        """Singleton accessor for in-memory corpus."""
        if cls._instance is None:
            cls._instance = DataLoader()
        return cls._instance

    def _load_all(self):
        """Loads and indexes all local files."""
        # 1. Load Scheme JSON files
        for scheme_id in VALID_SCHEME_IDS:
            scheme_file = PARSED_DIR / f"{scheme_id}.json"
            if scheme_file.exists():
                with open(scheme_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.schemes_data[scheme_id] = data
                    
                    # Index text blocks by section_title for O(1) lookup
                    blocks_dict = {}
                    for block in data.get("text_blocks", []):
                        title = block.get("section_title", "").strip()
                        text = block.get("text", "").strip()
                        blocks_dict[title.lower()] = text
                    self.scheme_text_blocks[scheme_id] = blocks_dict

        # 2. Load Analyzed Themes
        if ANALYZED_THEMES_PATH.exists():
            with open(ANALYZED_THEMES_PATH, "r", encoding="utf-8") as f:
                self.themes_data = json.load(f)
                for theme in self.themes_data.get("allThemes", []):
                    self.theme_lookup[theme["id"]] = theme

        # 3. Load Normalized Reviews (for acceptance test runner & verification)
        if NORMALIZED_REVIEWS_PATH.exists():
            with open(NORMALIZED_REVIEWS_PATH, "r", encoding="utf-8") as f:
                self.reviews = json.load(f)

    def get_scheme_section_text(self, scheme_id: str, section_title: str) -> Optional[str]:
        """Returns the exact text for a scheme section or None."""
        blocks = self.scheme_text_blocks.get(scheme_id)
        if not blocks:
            return None
        return blocks.get(section_title.strip().lower())

    def get_scheme_source_url(self, scheme_id: str) -> Optional[str]:
        """Returns the canonical Groww citation URL for a scheme."""
        scheme = self.schemes_data.get(scheme_id)
        return scheme.get("source_url") if scheme else None

    def get_scheme_name(self, scheme_id: str) -> Optional[str]:
        """Returns the formal name for a scheme."""
        scheme = self.schemes_data.get(scheme_id)
        if scheme and "scheme_name" in scheme:
            return scheme["scheme_name"]
        return SCHEME_NAMES.get(scheme_id)

    def get_scheme_nav_date(self, scheme_id: str) -> Optional[str]:
        """Returns the NAV date of the scheme."""
        scheme = self.schemes_data.get(scheme_id)
        return scheme.get("nav_date") if scheme else None

    def get_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        """Returns theme object including count, avgRating, and reviewIds."""
        return self.theme_lookup.get(theme_id)

    def is_top_theme(self, theme_id: str) -> bool:
        """Checks if a theme is in topThemes."""
        top_themes = self.themes_data.get("topThemes", [])
        return any(t.get("id") == theme_id for t in top_themes)
