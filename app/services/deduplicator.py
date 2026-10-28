from typing import List
from app.schemas.finding import Finding

class FindingDeduplicator:
    """
    Deduplicates overlapping findings from deterministic analyzers and LLM reasoning.
    Preserves provenance across multiple sources and selects the highest confidence
    and most actionable suggestions/autofixes.
    """

    def deduplicate(self, findings: List[Finding]) -> List[Finding]:
        merged_findings = {}

        for finding in findings:
            line = finding.start_line if finding.start_line is not None else 0
            
            # Normalized key: file + category + start_line
            # If line is 0 (file-wide), differentiate by title snippet to avoid collisions
            if line > 0:
                key = f"{finding.file}_{finding.category.value}_{line}"
            else:
                key = f"{finding.file}_{finding.category.value}_0_{finding.title.lower()[:20]}"

            if key in merged_findings:
                existing = merged_findings[key]
                
                # Merge sources to preserve provenance (e.g., "gcc_compiler, static_analyzer, llm")
                sources = set(s.strip() for s in existing.source.split(","))
                new_sources = set(s.strip() for s in finding.source.split(","))
                all_sources = sorted(list(sources.union(new_sources)))
                existing.source = ", ".join(all_sources)

                # Keep the highest confidence
                existing.confidence = round(max(existing.confidence, finding.confidence), 2)

                # Prefer richer titles over generic compiler diagnostics
                if "diagnostic:" in existing.title.lower() and "diagnostic:" not in finding.title.lower():
                    existing.title = finding.title

                # Prefer richer suggestions and explanations
                if len(finding.suggestion or "") > len(existing.suggestion or ""):
                    existing.suggestion = finding.suggestion

                if len(finding.explanation or "") > len(existing.explanation or ""):
                    existing.explanation = finding.explanation

                # Preserve autofix if found
                if not existing.autofix and finding.autofix:
                    existing.autofix = finding.autofix
            else:
                merged_findings[key] = finding

        return list(merged_findings.values())
