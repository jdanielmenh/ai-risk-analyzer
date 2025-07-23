from enum import Enum

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
