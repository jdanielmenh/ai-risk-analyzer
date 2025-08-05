from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntentLabel(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"


class IntentResponse(BaseModel):
    label: IntentLabel = Field(
        default=IntentLabel.INVALID,
        description="Classification result produced by the intent-router node.",
    )

    def __str__(self) -> str:  # pragma: no cover
        return self.label


class APICall(BaseModel):
    """Represents a single API call to be made."""

    endpoint: str = Field(
        description="The FMP API endpoint alias from FreeRiskAPI enum"
    )
    params: dict[str, Any] = Field(
        default_factory=dict, description="Parameters needed for the API call"
    )
    purpose: str = Field(
        description="What specific data this API call provides to answer the question"
    )


class ExecutionPlan(BaseModel):
    """The execution plan created by the planner node."""

    company_symbol: str | None = Field(
        default=None, description="The main company symbol being analyzed"
    )
    api_calls: list[APICall] = Field(
        default_factory=list,
        description="List of API calls needed to answer the specific question",
    )
    reasoning: str = Field(
        description="Explanation of why these specific API calls are needed to answer the question"
    )
    analysis_focus: str = Field(
        description="The specific aspect or mechanism that the question is asking about"
    )


class ReasonerAnswer(BaseModel):
    """Format that the reasoner node must return."""

    direct_answer: str = Field(description="2-3 sentences that answer the question")
    supporting_analysis: str = Field(
        description="Analysis and figures that support the answer"
    )
    current_position: str | None = Field(
        default=None,
        description="Current situation of the company regarding the risk factor",
    )
    potential_impact: str | None = Field(
        default=None, description="Magnitude and direction of the potential impact"
    )
