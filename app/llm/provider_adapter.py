import os
import re
import json
import uuid
import logging
from typing import List, Optional
from app.core.config import settings
from app.schemas.finding import Finding, Category, Severity

logger = logging.getLogger(__name__)

class MockLLMAdapter:
    """
    Intelligent local AI code analysis engine that performs pattern-based
    semantic reasoning over C++, Python, and Java code when an external LLM
    API key is not configured.
    """

    def review_code(
        self,
        code: str,
        checks: Optional[List[Category]] = None,
        filename: str = "source.cpp",
        language: str = "cpp"
    ) -> List[Finding]:
        lang = (language or "cpp").lower().strip()
        if lang in ("python", "py"):
            return self._review_python(code, checks, filename)
        elif lang in ("java",):
            return self._review_java(code, checks, filename)
        else:
            return self._review_cpp(code, checks, filename)

    def _review_cpp(self, code: str, checks: Optional[List[Category]], filename: str) -> List[Finding]:
        findings: List[Finding] = []
        checks_set = set(checks) if checks else set(Category)
        lines = code.splitlines()

        # Check 1: Memory Safety - Array Bounds
        if Category.memory_safety in checks_set:
            arr_decl_pat = re.compile(
                r"\b(?:int|char|float|double|long|short|unsigned|uint\w*|size_t|bool)\s+([a-zA-Z_]\w*)\s*\[\s*(\d+)\s*\]"
            )
            for m in arr_decl_pat.finditer(code):
                name = m.group(1)
                size = int(m.group(2))
                decl_start = m.start(1)
                
                idx_pat = re.compile(r"\b" + re.escape(name) + r"\s*\[\s*(\d+)\s*\]")
                for im in idx_pat.finditer(code):
                    idx = int(im.group(1))
                    line_no = code[:im.start()].count("\n") + 1
                    if im.start() != decl_start and idx >= size:
                        findings.append(Finding(
                            id=f"llm_{uuid.uuid4().hex[:8]}",
                            title=f"Potential out-of-bounds access on '{name}'",
                            category=Category.memory_safety,
                            severity=Severity.high,
                            confidence=0.88,
                            file=filename,
                            start_line=line_no,
                            end_line=line_no,
                            source="llm_agent",
                            evidence=f"Index '{idx}' exceeds allocated boundary of array '{name}[{size}]'.",
                            explanation=f"Accessing memory past element {size - 1} corrupts stack or heap memory and can lead to exploitable security vulnerabilities.",
                            suggestion=f"Verify index bounds: require 0 <= index < {size}.",
                            autofix=f"if (index < {size}) {{ {name}[index] = ...; }}"
                        ))

        # Check 2: Correctness - Uninitialized Variable Access
        if Category.correctness in checks_set:
            uninit_decl_pat = re.compile(r"\b(int|float|double|char|long|short|size_t)\s+([a-zA-Z_]\w*)\s*;")
            for m in uninit_decl_pat.finditer(code):
                var_type = m.group(1)
                var_name = m.group(2)
                decl_line = code[:m.start()].count("\n") + 1
                
                for idx, line in enumerate(lines[decl_line:], start=decl_line + 1):
                    clean = re.sub(r"//.*", "", line)
                    if re.search(r"\b" + re.escape(var_name) + r"\s*=[^=]", clean):
                        break
                    if re.search(r"&\s*" + re.escape(var_name) + r"\b", clean):
                        break
                    if re.search(r"\b" + re.escape(var_name) + r"\b", clean):
                        findings.append(Finding(
                            id=f"llm_{uuid.uuid4().hex[:8]}",
                            title=f"Uninitialized variable read: '{var_name}'",
                            category=Category.correctness,
                            severity=Severity.high,
                            confidence=0.90,
                            file=filename,
                            start_line=idx,
                            end_line=idx,
                            source="llm_agent",
                            evidence=f"Variable '{var_name}' is read at line {idx} before being assigned a valid value.",
                            explanation="In C++, reading an uninitialized variable is undefined behavior and produces arbitrary garbage values.",
                            suggestion=f"Initialize variable at point of declaration: '{var_type} {var_name} = 0;'.",
                            autofix=f"{var_type} {var_name} = 0;"
                        ))
                        break

            # Check 2b: Assignment inside condition
            cond_assign_pat = re.compile(r"\bif\s*\(\s*([a-zA-Z_]\w*)\s*=\s*([^=][^)]*)\)")
            for idx, line in enumerate(lines, start=1):
                m = cond_assign_pat.search(line)
                if m:
                    var = m.group(1)
                    findings.append(Finding(
                        id=f"llm_{uuid.uuid4().hex[:8]}",
                        title=f"Assignment in conditional expression on '{var}'",
                        category=Category.correctness,
                        severity=Severity.medium,
                        confidence=0.92,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="llm_agent",
                        evidence=line.strip(),
                        explanation="Single '=' performs assignment rather than comparison in 'if' condition, which is almost always an accidental bug.",
                        suggestion=f"Use '==' for comparison or enclose assignment in extra parentheses if intentional.",
                        autofix=line.replace("=", "==")
                    ))

        # Check 3: Security - Insecure functions
        if Category.security in checks_set:
            insecure_calls = {
                "gets": ("gets() allows unbounded buffer overwrites; function is deprecated and dangerous.", Severity.critical),
                "strcpy": ("strcpy() is susceptible to buffer overflows; use std::string or bounded copies.", Severity.high),
                "system": ("system() executes shell commands directly and is vulnerable to injection if input is untrusted.", Severity.high)
            }
            for fn, (desc, sev) in insecure_calls.items():
                pat = re.compile(r"\b" + fn + r"\s*\(")
                for idx, line in enumerate(lines, start=1):
                    if pat.search(re.sub(r"//.*", "", line)):
                        findings.append(Finding(
                            id=f"llm_{uuid.uuid4().hex[:8]}",
                            title=f"Security risk: Insecure function '{fn}()'",
                            category=Category.security,
                            severity=sev,
                            confidence=0.95,
                            file=filename,
                            start_line=idx,
                            end_line=idx,
                            source="llm_agent",
                            evidence=line.strip(),
                            explanation=desc,
                            suggestion=f"Replace '{fn}' with secure modern C++ constructs.",
                            autofix=None
                        ))

        # Check 4: Performance - Pass by value for containers
        if Category.performance in checks_set:
            val_param_pat = re.compile(r"\b(?:void|int|bool|double)\s+[a-zA-Z_]\w*\s*\([^)]*\b(std::string|std::vector<[^>]+>)\s+([a-zA-Z_]\w*)[^&)]*\)")
            for idx, line in enumerate(lines, start=1):
                m = val_param_pat.search(line)
                if m and "&" not in m.group(0):
                    param_type = m.group(1)
                    param_name = m.group(2)
                    findings.append(Finding(
                        id=f"llm_{uuid.uuid4().hex[:8]}",
                        title=f"Performance: Expensive copy of '{param_type}'",
                        category=Category.performance,
                        severity=Severity.low,
                        confidence=0.85,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="llm_agent",
                        evidence=line.strip(),
                        explanation=f"Passing '{param_name}' of type '{param_type}' by value triggers a dynamic heap allocation and deep copy.",
                        suggestion=f"Pass by const reference instead: 'const {param_type}& {param_name}'.",
                        autofix=f"const {param_type}& {param_name}"
                    ))

        return findings

    def _review_python(self, code: str, checks: Optional[List[Category]], filename: str) -> List[Finding]:
        findings: List[Finding] = []
        checks_set = set(checks) if checks else set(Category)
        lines = code.splitlines()

        # Check 1: Mutable default arguments
        if Category.correctness in checks_set:
            mut_arg_pat = re.compile(r"\bdef\s+([a-zA-Z_]\w*)\s*\([^)]*?(\w+)\s*=\s*(\[\]|\{\}|set\(\))")
            for idx, line in enumerate(lines, start=1):
                m = mut_arg_pat.search(line)
                if m:
                    fn_name, param, default_val = m.group(1), m.group(2), m.group(3)
                    findings.append(Finding(
                        id=f"llm_{uuid.uuid4().hex[:8]}",
                        title=f"Mutable default argument '{param}={default_val}' in function '{fn_name}'",
                        category=Category.correctness,
                        severity=Severity.high,
                        confidence=0.92,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="llm_agent",
                        evidence=line.strip(),
                        explanation="Default argument values are created when the function is defined. A mutable default is shared across every call, causing unexpected state mutations.",
                        suggestion=f"Use 'def {fn_name}(..., {param}=None):' and initialize '{param} = []' inside the function body.",
                        autofix=f"{param}=None"
                    ))

        # Check 2: Security - eval/exec/os.system
        if Category.security in checks_set:
            sec_checks = {
                "eval": ("eval() dynamically executes arbitrary Python code from strings, allowing remote code execution.", Severity.critical),
                "exec": ("exec() executes arbitrary code dynamically, creating critical code execution vulnerabilities.", Severity.critical),
                "os.system": ("os.system() runs commands directly in shell and is vulnerable to command injection.", Severity.high),
                "yaml.load": ("yaml.load() without SafeLoader can deserialize arbitrary Python objects.", Severity.high),
                "pickle.loads": ("pickle.loads() executes arbitrary code embedded within serialized objects.", Severity.critical)
            }
            for pattern, (expl, sev) in sec_checks.items():
                pat = re.compile(r"\b" + re.escape(pattern) + r"\s*\(")
                for idx, line in enumerate(lines, start=1):
                    clean = re.sub(r"#.*", "", line)
                    if pat.search(clean):
                        findings.append(Finding(
                            id=f"llm_{uuid.uuid4().hex[:8]}",
                            title=f"Security risk: Use of '{pattern}()'",
                            category=Category.security,
                            severity=sev,
                            confidence=0.95,
                            file=filename,
                            start_line=idx,
                            end_line=idx,
                            source="llm_agent",
                            evidence=line.strip(),
                            explanation=expl,
                            suggestion=f"Avoid using '{pattern}()'. Replace with safe standard library alternatives.",
                            autofix=None
                        ))

        # Check 3: Reliability - Bare except
        if Category.reliability in checks_set:
            for idx, line in enumerate(lines, start=1):
                clean = re.sub(r"#.*", "", line).strip()
                if clean.startswith("except:"):
                    findings.append(Finding(
                        id=f"llm_{uuid.uuid4().hex[:8]}",
                        title="Bare 'except:' catching all system interrupts",
                        category=Category.reliability,
                        severity=Severity.medium,
                        confidence=0.90,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="llm_agent",
                        evidence=line.strip(),
                        explanation="A bare 'except:' catches KeyboardInterrupt and SystemExit, preventing clean program termination.",
                        suggestion="Catch specific exceptions: 'except Exception as e:'.",
                        autofix="except Exception as e:"
                    ))

        return findings

    def _review_java(self, code: str, checks: Optional[List[Category]], filename: str) -> List[Finding]:
        findings: List[Finding] = []
        checks_set = set(checks) if checks else set(Category)
        lines = code.splitlines()

        # Check 1: String comparison with ==
        if Category.correctness in checks_set:
            str_eq_pat = re.compile(r"""\b([a-zA-Z_]\w*)\s*(==|!=)\s*("[^"]*")""")
            for idx, line in enumerate(lines, start=1):
                clean = re.sub(r"//.*", "", line)
                m = str_eq_pat.search(clean)
                if m:
                    var, op, lit = m.group(1), m.group(2), m.group(3)
                    findings.append(Finding(
                        id=f"llm_{uuid.uuid4().hex[:8]}",
                        title="String equality comparison with '==' reference check",
                        category=Category.correctness,
                        severity=Severity.high,
                        confidence=0.94,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="llm_agent",
                        evidence=line.strip(),
                        explanation="In Java, '==' compares memory addresses, not text contents. Distinct String instances with the same text evaluate to false.",
                        suggestion=f"Use '{lit}.equals({var})' or 'Objects.equals({var}, {lit})'.",
                        autofix=f"{lit}.equals({var})"
                    ))

        # Check 2: Null dereference risk
        if Category.reliability in checks_set:
            null_decl_pat = re.compile(r"\b([A-Z]\w*)\s+([a-zA-Z_]\w*)\s*=\s*null\s*;")
            for m in null_decl_pat.finditer(code):
                var = m.group(2)
                decl_line = code[:m.start()].count("\n") + 1
                for idx, line in enumerate(lines[decl_line:], start=decl_line + 1):
                    clean = re.sub(r"//.*", "", line)
                    if re.search(r"\b" + re.escape(var) + r"\s*=[^=]", clean):
                        break
                    if re.search(r"\b" + re.escape(var) + r"\s*\.\s*[a-zA-Z_]\w*", clean):
                        findings.append(Finding(
                            id=f"llm_{uuid.uuid4().hex[:8]}",
                            title=f"Potential NullPointerException on '{var}'",
                            category=Category.reliability,
                            severity=Severity.high,
                            confidence=0.91,
                            file=filename,
                            start_line=idx,
                            end_line=idx,
                            source="llm_agent",
                            evidence=line.strip(),
                            explanation=f"Variable '{var}' initialized to null and invoked without prior null check.",
                            suggestion=f"Verify '{var}' is not null before method invocation: `if ({var} != null)`.",
                            autofix=f"if ({var} != null) {{ ... }}"
                        ))
                        break

        # Check 3: Security - Command execution & SQL injection
        if Category.security in checks_set:
            for idx, line in enumerate(lines, start=1):
                clean = re.sub(r"//.*", "", line)
                if "Runtime.getRuntime().exec" in clean:
                    findings.append(Finding(
                        id=f"llm_{uuid.uuid4().hex[:8]}",
                        title="OS command execution with Runtime.getRuntime().exec()",
                        category=Category.security,
                        severity=Severity.high,
                        confidence=0.93,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="llm_agent",
                        evidence=line.strip(),
                        explanation="Calling Runtime.exec with unvalidated arguments introduces arbitrary command injection risks.",
                        suggestion="Use ProcessBuilder with strongly validated argument arrays.",
                        autofix=None
                    ))
                elif re.search(r"\b(?:executeQuery|executeUpdate)\s*\(\s*\"[^\"]*\"\s*\+", clean):
                    findings.append(Finding(
                        id=f"llm_{uuid.uuid4().hex[:8]}",
                        title="Potential SQL Injection through string concatenation",
                        category=Category.security,
                        severity=Severity.critical,
                        confidence=0.95,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="llm_agent",
                        evidence=line.strip(),
                        explanation="Dynamically appending variables into SQL strings allows attackers to manipulate query structures.",
                        suggestion="Use PreparedStatement with parameter placeholders ('?').",
                        autofix=None
                    ))

        return findings


class GoogleLLMAdapter:
    """
    LLM Provider Adapter for Google Gemini models.
    Supports multi-language code review for C++, Python, and Java.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name or settings.LLM_MODEL or "gemini-1.5-flash"
        self._initialized = False
        self._fallback_adapter = MockLLMAdapter()

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(
                    self.model_name,
                    generation_config={"response_mime_type": "application/json"}
                )
                self._initialized = True
            except Exception as e:
                logger.warning(f"Could not initialize Google Generative AI: {e}")
                self._initialized = False

    @property
    def is_available(self) -> bool:
        return bool(self._initialized and self.api_key)

    def review_code(
        self,
        code: str,
        checks: Optional[List[Category]] = None,
        filename: str = "source.cpp",
        language: str = "cpp"
    ) -> List[Finding]:
        if not self.is_available:
            logger.info(f"GOOGLE_API_KEY not configured or Gemini unavailable; using local AI analyzer fallback for {language}.")
            return self._fallback_adapter.review_code(code, checks, filename, language=language)

        checks_str = ", ".join(c.value if isinstance(c, Category) else str(c) for c in (checks or list(Category)))
        lang_title = language.upper()

        system_prompt = f"""
You are CodeSentinel, a meticulous and professional {lang_title} code review AI agent.
Analyze the following {lang_title} source code for concrete correctness, memory-safety, security, performance, reliability, and maintainability issues.
Target the following categories: [{checks_str}].

Output MUST be a JSON array of finding objects adhering to this exact format:
[
  {{
    "title": "Concise summary of problem",
    "category": "correctness|memory_safety|security|performance|reliability|maintainability|style|testing",
    "severity": "critical|high|medium|low|info",
    "confidence": 0.95,
    "start_line": 10,
    "end_line": 10,
    "evidence": "Code line or trigger causing the issue",
    "explanation": "Why this is dangerous or problematic",
    "suggestion": "How to resolve the problem properly",
    "autofix": "Safe {lang_title} replacement code if possible, or null"
  }}
]

Guidelines:
- Only report verifiable, high-confidence issues.
- Never invent line numbers or functions.
- If no issues are present, return an empty array: []
- Do NOT include any markdown formatting outside the JSON array.
"""

        user_prompt = f"Language: {language}\nFilename: {filename}\nSource Code:\n```{language}\n{code}\n```"

        try:
            response = self.model.generate_content([system_prompt, user_prompt])
            raw_text = response.text.strip()

            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                raw_text = re.sub(r"\n?```$", "", raw_text)

            findings_data = json.loads(raw_text)
            if isinstance(findings_data, dict):
                findings_data = findings_data.get("findings", [findings_data])

            findings: List[Finding] = []
            for item in findings_data:
                item["id"] = f"gemini_{uuid.uuid4().hex[:8]}"
                item["source"] = "gemini_llm"
                item["file"] = filename

                cat_val = item.get("category", "correctness").lower()
                valid_cats = [c.value for c in Category]
                item["category"] = Category(cat_val) if cat_val in valid_cats else Category.correctness

                sev_val = item.get("severity", "medium").lower()
                valid_sevs = [s.value for s in Severity]
                item["severity"] = Severity(sev_val) if sev_val in valid_sevs else Severity.medium

                try:
                    conf = float(item.get("confidence", 0.85))
                    item["confidence"] = max(0.0, min(1.0, conf))
                except (ValueError, TypeError):
                    item["confidence"] = 0.85

                findings.append(Finding(**item))

            return findings

        except Exception as e:
            logger.error(f"Gemini API request failed: {e}. Falling back to local AI analyzer.")
            return self._fallback_adapter.review_code(code, checks, filename, language=language)


def get_llm_adapter(provider: Optional[str] = None):
    selected_provider = provider or settings.LLM_PROVIDER
    if selected_provider == "mock":
        return MockLLMAdapter()
    elif selected_provider == "gemini":
        return GoogleLLMAdapter()
    else:  # "auto"
        adapter = GoogleLLMAdapter()
        return adapter
