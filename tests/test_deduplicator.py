from app.schemas.finding import Finding, Category, Severity
from app.services.deduplicator import FindingDeduplicator

def test_deduplicator_merges_same_line_and_category():
    dedup = FindingDeduplicator()
    f1 = Finding(
        id="f1",
        title="Diagnostic: array bounds",
        category=Category.memory_safety,
        severity=Severity.high,
        confidence=0.8,
        file="main.cpp",
        start_line=10,
        end_line=10,
        source="gcc_compiler",
        evidence="Warning: array bounds",
        explanation="Bounds error",
        suggestion="Short suggestion"
    )
    f2 = Finding(
        id="f2",
        title="Array out of bounds on 'arr'",
        category=Category.memory_safety,
        severity=Severity.high,
        confidence=0.95,
        file="main.cpp",
        start_line=10,
        end_line=10,
        source="static_analyzer",
        evidence="Accessed index 10 on size 5",
        explanation="Detailed impact explanation",
        suggestion="A much more detailed actionable fix suggestion",
        autofix="int x = 0;"
    )

    merged = dedup.deduplicate([f1, f2])
    assert len(merged) == 1
    result = merged[0]
    assert result.confidence == 0.95
    assert "gcc_compiler" in result.source
    assert "static_analyzer" in result.source
    assert result.autofix == "int x = 0;"
    assert result.title == "Array out of bounds on 'arr'"
