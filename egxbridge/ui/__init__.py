"""Dashboard UI helpers. Orchestration only — no scoring or provider logic."""

DEFAULT_PAGE = "Daily Operator"
OPERATE_PAGES = [
    "Daily Operator",
    "Explorer Candidates",
    "Analysis Workflows",
    "Schedule Analysis Center",
    "Forward Validation Lab",
    "Signal Outcomes",
]
TECHNICAL_PAGES = [
    "Whole Market",
    "Symbol Explorer",
    "Candles",
    "Provider Status",
    "Data Quality",
    "Source Conflicts",
    "Collection Health",
    "System Overview",
]
ALL_PAGES = OPERATE_PAGES + TECHNICAL_PAGES
