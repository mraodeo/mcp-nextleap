"""
Pattern Agent: Historical Review Trend Analytics.
Maps user complaints to Milestone 2 themes and evaluates volume/recurrence patterns.
"""
from typing import Dict, Any
from src.state import AgentGraphState, PatternOutput
from src.data_loader import DataLoader
from src.config import VALID_THEME_IDS, REVIEW_WINDOW

def mock_or_call_pattern_llm(sanitized_text: str) -> str:
    """
    Classifies the user complaint to exactly one theme ID from allThemes.
    """
    text_lower = sanitized_text.lower()
    
    # Priority matching: financial loss/fees > money movement > trading > app stability
    if any(k in text_lower for k in [
        "fee", "fees", "brokerage", "exit load", "exit-load",
        "charge", "charges", "deducted fee", "hidden charges", "stamp duty"
    ]):
        return "fees_brokerage"
    elif any(k in text_lower for k in [
        "withdraw", "withdrawal", "deposit", "deposits", "payment",
        "payments", "bank", "refund", "upi", "deducted from bank", "balance"
    ]):
        return "money_movement"
    elif any(k in text_lower for k in [
        "chart", "charts", "candlestick", "order", "orders",
        "trade", "trading", "buy", "sell", "executed"
    ]):
        return "trading_charts"
    elif any(k in text_lower for k in [
        "crash", "crashes", "slow", "lag", "bug", "stuck",
        "login", "freeze", "server", "fingerprint", "android", "down"
    ]):
        return "reliability"
    
    return "other"

def pattern_agent_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Pattern Agent Node: Runs concurrently in parallel fan-out.
    """
    sanitized_input = state["sanitized_input"]
    data_loader = DataLoader.get_instance()

    # 1. Single classification call
    theme_id = mock_or_call_pattern_llm(sanitized_input)
    if theme_id not in VALID_THEME_IDS:
        theme_id = "other"

    # 2. Deterministic Analytics over Milestone 2 data
    theme_info = data_loader.get_theme(theme_id) or {
        "id": theme_id,
        "name": "Other feedback",
        "count": 0,
        "avgRating": 3.0,
        "reviewIds": []
    }

    count = theme_info.get("count", len(theme_info.get("reviewIds", [])))
    avg_rating = theme_info.get("avgRating", 3.0)

    # Status heuristics based on quantitative thresholds:
    # - recurring: count >= 100 and avg rating <= 2.5 (e.g. fees_brokerage, reliability, money_movement)
    # - rising: in topThemes or high-velocity trading/payment issues
    # - one-off: otherwise
    if count >= 100 and avg_rating <= 2.5:
        pattern_status = "recurring"
    elif theme_id in ["trading_charts", "money_movement"] or data_loader.is_top_theme(theme_id):
        pattern_status = "rising"
    else:
        pattern_status = "one-off"

    in_top = data_loader.is_top_theme(theme_id)

    pattern_output: PatternOutput = {
        "theme_id": theme_id,
        "theme_name": theme_info.get("name", theme_id),
        "status": pattern_status,
        "review_count": count,
        "review_window": REVIEW_WINDOW,
        "in_top_themes": in_top
    }

    return {"pattern": pattern_output, "fired_agents_log": ["pattern_agent"]}
