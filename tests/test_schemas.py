import pytest
from pydantic import ValidationError
from app.schemas.finding import Finding, Category, Severity
from app.schemas.review import ReviewRequest, ReviewResponse

def test_finding_creation_valid():
    finding = Finding(
        id="f1",
        title="Out of bounds",
        category=Category.memory_safety,
        severity=Severity.high,
        confidence=0.9,
        file="test.cpp",
        start_line=5,
        end_line=5,
        source="test",
        evidence="arr[10] on arr[5]",
        explanation="Index exceeds array bounds",
        suggestion="Check bounds"
    )
    assert finding.id == "f1"
    assert finding.confidence == 0.9
    assert finding.category == Category.memory_safety

def test_finding_invalid_confidence():
    with pytest.raises(ValidationError):
        Finding(
            id="f2",
            title="Invalid",
            category=Category.security,
            severity=Severity.low,
            confidence=1.5,  # Must be <= 1.0
            file="test.cpp",
            source="test",
            evidence="",
            explanation="",
            suggestion=""
        )

def test_review_request_and_response():
    req = ReviewRequest(
        language="cpp",
        code="int main() { return 0; }",
        filename="main.cpp"
    )
    assert req.language == "cpp"
    assert len(req.checks) == 5

    resp = ReviewResponse(
        review_id="rev_123",
        status="completed",
        findings=[]
    )
    assert resp.review_id == "rev_123"
    assert resp.findings == []
