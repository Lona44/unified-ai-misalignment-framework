from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0"

class TraceProvenance(str, Enum):
    FULL = "full"             # raw chain-of-thought (rare; not exposed by Claude 4 / o-series)
    SUMMARIZED = "summarized" # provider-summarized reasoning
    OMITTED = "omitted"       # model withheld text (signature only)
    NONE = "none"             # no reasoning this step (direct action / baseline)

class ThinkingTrace(BaseModel):
    available: bool = False
    provenance: TraceProvenance = TraceProvenance.NONE
    text: Optional[str] = None
    tokens: int = 0

class ToolCall(BaseModel):
    name: str = "bash"
    command: str = ""
    output: str = ""
    return_code: Optional[int] = None

class StepEvent(BaseModel):
    schema_version: str = SCHEMA_VERSION
    experiment_id: str
    model: str
    implementation: str
    step: int
    thinking: ThinkingTrace = Field(default_factory=ThinkingTrace)
    tool_calls: list[ToolCall] = Field(default_factory=list)
