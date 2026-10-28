import re
from pydantic import BaseModel, Field, constr, field_validator
from typing import List
from app.schemas.finding import Category, Finding

class ReviewRequest(BaseModel):
    language: str = Field(
        default="cpp",
        description="Programming language of the source code (cpp, python, java)"
    )
    code: constr(min_length=1, max_length=50000) = Field(..., description="Source code to review")
    checks: List[Category] = Field(
        default_factory=lambda: [
            Category.security,
            Category.memory_safety,
            Category.correctness,
            Category.reliability,
            Category.performance
        ]
    )
    filename: str = Field(..., description="Name of the file being reviewed")

    @field_validator("language")
    @classmethod
    def normalize_language(cls, v: str) -> str:
        lang = v.strip().lower()
        if lang in ("c++", "cpp", "cxx"):
            return "cpp"
        elif lang in ("python", "py", "python3"):
            return "python"
        elif lang in ("java",):
            return "java"
        else:
            raise ValueError(f"Unsupported language '{v}'. Supported: cpp, python, java")

class ReviewResponse(BaseModel):
    review_id: str
    status: str
    findings: List[Finding]
