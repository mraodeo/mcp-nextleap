"""
Unit tests for DataLoader.
Validates loading, indexing, and querying of schemes, text blocks, themes, and reviews.
"""
from src.data_loader import DataLoader
from src.config import VALID_SCHEME_IDS, VALID_SECTIONS, CANONICAL_NAV_DATE

def test_data_loader_singleton():
    loader1 = DataLoader.get_instance()
    loader2 = DataLoader.get_instance()
    assert loader1 is loader2

def test_all_schemes_loaded():
    loader = DataLoader.get_instance()
    for scheme_id in VALID_SCHEME_IDS:
        assert scheme_id in loader.schemes_data, f"Scheme {scheme_id} missing from loaded schemes"
        name = loader.get_scheme_name(scheme_id)
        assert name is not None and len(name) > 0
        url = loader.get_scheme_source_url(scheme_id)
        assert url is not None and url.startswith("https://groww.in/mutual-funds/")
        nav_date = loader.get_scheme_nav_date(scheme_id)
        assert nav_date == CANONICAL_NAV_DATE

def test_exit_load_text_blocks():
    loader = DataLoader.get_instance()
    # Large Cap, Mid Cap, Small Cap: 1% within 1 year
    for equity_id in ["large_cap", "mid_cap", "small_cap"]:
        exit_load_text = loader.get_scheme_section_text(equity_id, "Exit load")
        assert exit_load_text is not None
        assert "1% if redeemed within 1 year" in exit_load_text

    # Gold FoF and Silver FoF: 1% within 15 days
    for fof_id in ["gold_fof", "silver_fof"]:
        exit_load_text = loader.get_scheme_section_text(fof_id, "Exit load")
        assert exit_load_text is not None
        assert "1%" in exit_load_text and "15 days" in exit_load_text

def test_stamp_duty_and_tax_block():
    loader = DataLoader.get_instance()
    tax_text = loader.get_scheme_section_text("large_cap", "Stamp duty and tax")
    assert tax_text is not None
    assert "0.005%" in tax_text
    assert "20%" in tax_text

def test_themes_loaded_and_queried():
    loader = DataLoader.get_instance()
    # Check that fees_brokerage theme exists
    fees = loader.get_theme("fees_brokerage")
    assert fees is not None
    assert fees["id"] == "fees_brokerage"
    assert fees["count"] == 136

    # Check that money_movement theme exists
    money = loader.get_theme("money_movement")
    assert money is not None
    assert money["count"] == 162
    assert loader.is_top_theme("money_movement") is True

    # Check reliability theme
    rel = loader.get_theme("reliability")
    assert rel is not None
    assert rel["count"] == 140

def test_reviews_corpus_loaded():
    loader = DataLoader.get_instance()
    assert len(loader.reviews) == 1650, f"Expected 1650 reviews, found {len(loader.reviews)}"
