from typing import Literal

from pydantic import BaseModel


class RouterState(BaseModel):
    question: str
    router_label: Literal["VALID", "INVALID"] | None = None
    answer: str | None = None
