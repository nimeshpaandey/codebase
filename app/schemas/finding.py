from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"

class Category(str, Enum):
    correctness = "correctness"
    memory_safety = "memory_safety"
    security = "security"
    performance = "performance"
    reliability = "reliability"
    maintainability = "maintainability"
    style = "style"
    testing = "testing"

class Finding(BaseModel):
    id: str = Field(..., description="Unique identifier for the finding")
    title: str = Field(..., description="Short summary of the issue")
    category: Category
    severity: Severity
    confidence: float = Field(..., ge=0.0, le=1.0)
    file: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    source: str = Field(..., description="e.g., llm, clang_tidy, clang_static_analyzer")
    evidence: str = Field(..., description="Why this is an issue based on the code")
    explanation: str = Field(..., description="Impact of the issue")
    suggestion: str = Field(..., description="Actionable fix")
    autofix: Optional[str] = None