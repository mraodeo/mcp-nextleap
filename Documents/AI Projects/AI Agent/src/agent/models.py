from pydantic import BaseModel, Field
from typing import List

class PulseReport(BaseModel):
    """
    Structured schema for the weekly review pulse report.
    This enforces the LLM to output exactly the fields required by the problem statement.
    """
    themes: List[str] = Field(
        description="The top 3 most prominent themes or topics discussed in the reviews.",
        min_items=1,
        max_items=3
    )
    quotes: List[str] = Field(
        description="3 exact, verbatim user quotes extracted directly from the reviews that highlight the top themes. Do not invent or paraphrase.",
        min_items=1,
        max_items=3
    )
    actions: List[str] = Field(
        description="3 concrete, actionable next steps for the Product/Growth or Support teams, grounded strictly in the extracted themes.",
        min_items=1,
        max_items=3
    )
