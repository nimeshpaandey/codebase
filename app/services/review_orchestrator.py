from typing import List, Optional
from app.schemas.review import ReviewRequest
from app.schemas.finding import Finding
from app.analyzers import get_analyzer_for_language
from app.llm.provider_adapter import get_llm_adapter
from app.services.deduplicator import FindingDeduplicator
from app.security.redaction import CodeRedactor

class ReviewOrchestrator:
    """
    Coordinates language-specific deterministic analysis and LLM semantic analysis
    for C++, Python, and Java codebases, enforcing privacy redaction and deduplication.
    """

    def __init__(self, llm_adapter=None, analyzer_override=None):
        self.analyzer_override = analyzer_override
        self.llm_adapter = llm_adapter or get_llm_adapter()
        self.deduplicator = FindingDeduplicator()
        self.redactor = CodeRedactor()

    def run_review(self, request: ReviewRequest) -> List[Finding]:
        all_findings: List[Finding] = []

        # 1. Deterministic checks for target language (runs locally on original code)
        analyzer = self.analyzer_override or get_analyzer_for_language(request.language)
        deterministic_findings = analyzer.analyze(request.code, request.filename)
        all_findings.extend(deterministic_findings)

        # 2. LLM reasoning (runs on REDACTED code to protect privacy)
        safe_code = self.redactor.redact(request.code)
        llm_findings = self.llm_adapter.review_code(
            safe_code,
            checks=request.checks,
            filename=request.filename,
            language=request.language
        )

        for finding in llm_findings:
            finding.file = request.filename
            all_findings.append(finding)

        # 3. Deduplicate overlapping findings
        deduped_findings = self.deduplicator.deduplicate(all_findings)

        # 4. Filter to requested checks if specified
        if request.checks:
            requested_cats = set(request.checks)
            final_findings = [f for f in deduped_findings if f.category in requested_cats]
        else:
            final_findings = deduped_findings

        return final_findings
