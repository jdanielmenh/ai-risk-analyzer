from typing import Any, Literal

from pydantic import BaseModel

from models.riskbot_models import ExecutionPlan


class ConversationState(BaseModel):
    question: str
    router_label: Literal["VALID", "INVALID"] | None = None
    execution_plan: ExecutionPlan | None = None
    api_results: dict[str, Any] | None = None
    answer: str | None = None
