import tempfile
import os
from app.repositories.review_repository import ReviewRepository
from app.schemas.finding import Finding, Category, Severity

def test_repository_save_and_retrieve():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        repo = ReviewRepository(db_path=db_path)

        finding = Finding(
            id="f_repo_1",
            title="Uninitialized var",
            category=Category.correctness,
            severity=Severity.high,
            confidence=0.92,
            file="code.cpp",
            start_line=15,
            end_line=15,
            source="static_analyzer",
            evidence="uninit_val used at L15",
            explanation="Causes undefined behavior",
            suggestion="Initialize variable",
            autofix="int uninit_val = 0;"
        )

        repo.save_review("rev_test_42", "completed", [finding])

        retrieved = repo.get_review("rev_test_42")
        assert retrieved is not None
        assert retrieved["review_id"] == "rev_test_42"
        assert retrieved["status"] == "completed"
        assert len(retrieved["findings"]) == 1
        
        saved_f = retrieved["findings"][0]
        assert saved_f.id == "f_repo_1"
        assert saved_f.start_line == 15
        assert saved_f.autofix == "int uninit_val = 0;"

        # Non-existent review
        assert repo.get_review("non_existent") is None
