import os
import sys
import argparse

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas.review import ReviewRequest
from app.services.review_orchestrator import ReviewOrchestrator

EVAL_BENCHMARKS = {
    "cpp": {
        "fixture": "tests/fixtures/cpp/bad_code.cpp",
        "filename": "bad_code.cpp",
        "expected_categories": ["memory_safety", "correctness"]
    },
    "python": {
        "fixture": "tests/fixtures/python/bad_code.py",
        "filename": "bad_code.py",
        "expected_categories": ["correctness", "security", "reliability"]
    },
    "java": {
        "fixture": "tests/fixtures/java/BadCode.java",
        "filename": "BadCode.java",
        "expected_categories": ["memory_safety", "correctness", "security"]
    }
}

def evaluate_language(orchestrator: ReviewOrchestrator, lang: str) -> dict:
    config = EVAL_BENCHMARKS[lang]
    with open(config["fixture"], "r", encoding="utf-8") as f:
        code = f.read()

    expected_categories = config["expected_categories"]
    request = ReviewRequest(language=lang, code=code, filename=config["filename"])
    findings = orchestrator.run_review(request)

    reported_categories = [f.category.value for f in findings]
    true_positives = sum(1 for exp in expected_categories if exp in reported_categories)

    total_reported = len(findings)
    total_expected = len(expected_categories)
    precision = (true_positives / total_reported) if total_reported > 0 else 0.0
    recall = (true_positives / total_expected) if total_expected > 0 else 0.0

    print(f"\n==========================================")
    print(f"  Evaluation Report: {lang.upper()}")
    print(f"==========================================")
    print(f"Total Findings Reported: {total_reported}")
    print(f"Expected Bugs Found (True Positives): {true_positives} / {total_expected}")
    print(f"Precision: {precision:.2f}")
    print(f"Recall:    {recall:.2f}")
    print("Reported Issues:")
    for f in findings:
        line_str = f"L{f.start_line}" if f.start_line else "File-wide"
        print(f" - [{f.category.value}] {f.title} ({line_str}, Source: {f.source})")

    return {
        "language": lang,
        "precision": precision,
        "recall": recall,
        "findings_count": total_reported
    }

def run_evaluation(language: str = "all"):
    orchestrator = ReviewOrchestrator()
    targets = [language] if language in EVAL_BENCHMARKS else list(EVAL_BENCHMARKS.keys())
    results = []

    for lang in targets:
        res = evaluate_language(orchestrator, lang)
        results.append(res)

    print("\n" + "=" * 42)
    print("  MULTI-LANGUAGE BENCHMARK SUMMARY")
    print("=" * 42)
    for r in results:
        status = "PASSED" if r["recall"] == 1.0 else "IMPROVE"
        print(f"[{status}] {r['language'].upper():<8} | Precision: {r['precision']:.2f} | Recall: {r['recall']:.2f} | Findings: {r['findings_count']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate CodeSentinel across languages")
    parser.add_argument("--lang", choices=["all", "cpp", "python", "java"], default="all")
    args = parser.parse_args()
    run_evaluation(args.lang)
