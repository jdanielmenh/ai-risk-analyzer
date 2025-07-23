from pydantic import BaseModel


class RouterState(BaseModel):
    query: str
    router_label: str = ""
