import os
import re
import shutil
import subprocess
import tempfile
import uuid
from typing import List, Optional
from app.schemas.finding import Finding, Category, Severity

class JavaAnalyzer:
    """
    Static analyzer for Java source code supporting:
    1. javac compiler lint diagnostics (-Xlint:all)
    2. Deterministic AST/pattern static analysis for string comparison bugs,
       array bounds, null dereference risks, unclosed resources, and security issues.
    """

    def analyze(self, code: str, filename: str = "Main.java") -> List[Finding]:
        findings: List[Finding] = []

        # 1. Run javac diagnostics if javac is installed
        if shutil.which("javac"):
            findings.extend(self._run_javac(code, filename))

        # 2. Run deterministic static pattern checks
        findings.extend(self._run_pattern_checks(code, filename))

        return findings

    def _run_javac(self, code: str, filename: str) -> List[Finding]:
        findings = []
        with tempfile.TemporaryDirectory() as temp_dir:
            # Determine class name from code if available, else use basename
            match = re.search(r"public\s+class\s+([A-Za-z_]\w*)", code)
            class_name = match.group(1) if match else "Main"
            source_filename = f"{class_name}.java"
            file_path = os.path.join(temp_dir, source_filename)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            try:
                result = subprocess.run(
                    ["javac", "-Xlint:all", source_filename],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stderr
                findings.extend(self._parse_javac_output(output, filename))
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass

        return findings

    def _parse_javac_output(self, output: str, filename: str) -> List[Finding]:
        findings = []
        # Pattern: File.java:12: warning: [tag] message
        pattern = re.compile(r"^.+?\.java:(\d+):\s+(warning|error):\s+(?:\[(.*?)\]\s+)?(.+)$")

        for line in output.splitlines():
            m = pattern.search(line.strip())
            if m:
                line_no = int(m.group(1))
                diag_type = m.group(2)
                tag = m.group(3) or "javac"
                message = m.group(4)

                category = Category.correctness
                severity = Severity.medium if diag_type == "warning" else Severity.high

                lower_msg = (message + " " + tag).lower()
                if "divzero" in tag or "division by zero" in lower_msg:
                    category = Category.correctness
                    severity = Severity.high
                elif "rawtypes" in tag or "unchecked" in tag:
                    category = Category.maintainability
                    severity = Severity.low
                elif "deprecation" in tag:
                    category = Category.maintainability
                    severity = Severity.low
                elif "try" in tag or "resource" in lower_msg:
                    category = Category.reliability
                    severity = Severity.medium
                elif "fallthrough" in tag:
                    category = Category.correctness
                    severity = Severity.medium

                findings.append(Finding(
                    id=f"javac_{uuid.uuid4().hex[:8]}",
                    title=f"Java compiler {diag_type}: [{tag}]",
                    category=category,
                    severity=severity,
                    confidence=0.96,
                    file=filename,
                    start_line=line_no,
                    end_line=line_no,
                    source="javac_compiler",
                    evidence=message,
                    explanation=f"Java compiler issued {diag_type} with tag [{tag}].",
                    suggestion="Address compiler diagnostic according to Java standard conventions.",
                    autofix=None
                ))

        return findings

    def _run_pattern_checks(self, code: str, filename: str) -> List[Finding]:
        findings = []
        lines = code.splitlines()

        # 1. String comparison with == or != instead of .equals()
        str_eq_pat1 = re.compile(r"""\b([a-zA-Z_]\w*)\s*(==|!=)\s*("[^"]*")""")
        str_eq_pat2 = re.compile(r"""("[^"]*")\s*(==|!=)\s*([a-zA-Z_]\w*)""")

        for idx, line in enumerate(lines, start=1):
            clean = re.sub(r"//.*", "", line)
            m = str_eq_pat1.search(clean) or str_eq_pat2.search(clean)
            if m:
                findings.append(Finding(
                    id=f"java_streq_{uuid.uuid4().hex[:8]}",
                    title="String comparison using reference equality ('==' or '!=')",
                    category=Category.correctness,
                    severity=Severity.high,
                    confidence=0.98,
                    file=filename,
                    start_line=idx,
                    end_line=idx,
                    source="java_analyzer",
                    evidence=line.strip(),
                    explanation=(
                        "In Java, '==' compares object memory references rather than string content values. "
                        "Two strings with identical characters may evaluate to false if they reside at different memory addresses."
                    ),
                    suggestion="Use '.equals()' or 'Objects.equals(a, b)' for value equality comparison.",
                    autofix=re.sub(r"""\b([a-zA-Z_]\w*)\s*==\s*("[^"]*")""", r"""\2.equals(\1)""", line.strip())
                ))

        # 2. Fixed array out-of-bounds detection
        arr_decl_pat = re.compile(
            r"\b(?:int|long|byte|short|double|float|char|boolean|String)\s*\[\s*\]\s+([a-zA-Z_]\w*)\s*=\s*new\s+\w+\s*\[\s*(\d+)\s*\]"
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
                        id=f"java_bounds_{uuid.uuid4().hex[:8]}",
                        title=f"Array index out of bounds on '{name}'",
                        category=Category.memory_safety,
                        severity=Severity.high,
                        confidence=0.98,
                        file=filename,
                        start_line=line_no,
                        end_line=line_no,
                        source="java_analyzer",
                        evidence=f"Array '{name}' declared with size {size} (indices 0..{size-1}), but accessed at index {idx}.",
                        explanation="Accessing an array outside its allocated bounds throws ArrayIndexOutOfBoundsException at runtime.",
                        suggestion=f"Ensure index is within [0, {size - 1}].",
                        autofix=f"// Ensure index < {size} before: {name}[{idx}]"
                    ))

        # 3. Potential NullPointerException (assigned null and dereferenced)
        null_assign_pat = re.compile(r"\b([A-Z]\w*)\s+([a-zA-Z_]\w*)\s*=\s*null\s*;")
        for m in null_assign_pat.finditer(code):
            var_name = m.group(2)
            decl_line = code[:m.start()].count("\n") + 1

            for idx, line in enumerate(lines[decl_line:], start=decl_line + 1):
                clean = re.sub(r"//.*", "", line)
                if re.search(r"\b" + re.escape(var_name) + r"\s*=[^=]", clean):
                    break  # Reassigned
                if re.search(r"\b" + re.escape(var_name) + r"\s*\.\s*[a-zA-Z_]\w*", clean):
                    findings.append(Finding(
                        id=f"java_npe_{uuid.uuid4().hex[:8]}",
                        title=f"Potential NullPointerException dereferencing null '{var_name}'",
                        category=Category.reliability,
                        severity=Severity.high,
                        confidence=0.92,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="java_analyzer",
                        evidence=line.strip(),
                        explanation=f"Variable '{var_name}' was assigned null at line {decl_line} and is dereferenced here without null check.",
                        suggestion=f"Initialize '{var_name}' with a non-null object or add a null check: `if ({var_name} != null)`.",
                        autofix=f"if ({var_name} != null) {{ ... }}"
                    ))
                    break

        # 4. Unclosed resources / streams
        resource_types = ["FileInputStream", "FileOutputStream", "FileReader", "FileWriter", "BufferedReader", "Scanner", "Socket"]
        res_pat = re.compile(r"\b(" + "|".join(resource_types) + r")\s+([a-zA-Z_]\w*)\s*=\s*new\s+\1\b")
        for idx, line in enumerate(lines, start=1):
            clean = re.sub(r"//.*", "", line)
            m = res_pat.search(clean)
            if m:
                # Check if inside try-with-resources "try ("
                if not re.search(r"\btry\s*\(", clean):
                    res_name = m.group(2)
                    findings.append(Finding(
                        id=f"java_res_{uuid.uuid4().hex[:8]}",
                        title=f"Unclosed resource leak: '{res_name}'",
                        category=Category.reliability,
                        severity=Severity.medium,
                        confidence=0.90,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="java_analyzer",
                        evidence=line.strip(),
                        explanation=f"Resource '{res_name}' may not be closed properly if an exception occurs, causing OS file handle or socket leaks.",
                        suggestion="Use modern try-with-resources statement: `try (Resource res = new Resource()) { ... }`.",
                        autofix=None
                    ))

        # 5. Empty catch blocks
        for idx, line in enumerate(lines, start=1):
            if re.search(r"catch\s*\([^)]+\)\s*\{\s*\}", line):
                findings.append(Finding(
                    id=f"java_catch_{uuid.uuid4().hex[:8]}",
                    title="Empty catch block silently suppressing exceptions",
                    category=Category.maintainability,
                    severity=Severity.medium,
                    confidence=0.95,
                    file=filename,
                    start_line=idx,
                    end_line=idx,
                    source="java_analyzer",
                    evidence=line.strip(),
                    explanation="Empty catch blocks swallow exceptions and cause failures to go undetected, making maintenance and debugging difficult.",
                    suggestion="Log the exception or re-throw as an unchecked/wrapped exception.",
                    autofix=None
                ))

        # 6. Insecure SQL Injection in JDBC
        sql_pat = re.compile(r"\b(?:executeQuery|executeUpdate|execute)\s*\(\s*\"[^\"]*\"\s*\+", re.IGNORECASE)
        for idx, line in enumerate(lines, start=1):
            if sql_pat.search(line):
                findings.append(Finding(
                    id=f"java_sqli_{uuid.uuid4().hex[:8]}",
                    title="Potential SQL Injection via query string concatenation",
                    category=Category.security,
                    severity=Severity.critical,
                    confidence=0.94,
                    file=filename,
                    start_line=idx,
                    end_line=idx,
                    source="java_analyzer",
                    evidence=line.strip(),
                    explanation="Constructing SQL queries with string concatenation allows attacker input to alter SQL execution logic.",
                    suggestion="Use `PreparedStatement` with parameterized placeholders ('?').",
                    autofix=None
                ))

        # 7. Command injection via Runtime.exec
        for idx, line in enumerate(lines, start=1):
            if re.search(r"Runtime\.getRuntime\(\)\.exec\s*\(", line):
                findings.append(Finding(
                    id=f"java_cmd_{uuid.uuid4().hex[:8]}",
                    title="Command execution via Runtime.getRuntime().exec()",
                    category=Category.security,
                    severity=Severity.high,
                    confidence=0.92,
                    file=filename,
                    start_line=idx,
                    end_line=idx,
                    source="java_analyzer",
                    evidence=line.strip(),
                    explanation="Executing external operating system commands via Runtime.exec can allow command injection vulnerabilities.",
                    suggestion="Use `ProcessBuilder` with an explicit array of command arguments.",
                    autofix=None
                ))

        return findings
