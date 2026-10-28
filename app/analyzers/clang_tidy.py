import os
import re
import shutil
import subprocess
import tempfile
import uuid
from typing import List, Optional
from app.schemas.finding import Finding, Category, Severity

class ClangTidyAnalyzer:
    """
    Static analyzer for C++ code supporting:
    1. clang-tidy (if installed in system PATH)
    2. GCC compiler diagnostic analysis (using g++ -Wall -Wextra)
    3. Deterministic AST/pattern static analysis for bounds, uninitialized variables,
       memory management, and unsafe C API usage.
    """

    def analyze(self, code: str, filename: str) -> List[Finding]:
        findings: List[Finding] = []
        
        # 1. Run clang-tidy if available
        if shutil.which("clang-tidy"):
            findings.extend(self._run_clang_tidy(code, filename))
            
        # 2. Run GCC diagnostics if g++ is available
        if shutil.which("g++"):
            findings.extend(self._run_gcc_analyzer(code, filename))
            
        # 3. Run deterministic static pattern checks
        findings.extend(self._run_pattern_checks(code, filename))
        
        return findings

    def _run_clang_tidy(self, code: str, filename: str) -> List[Finding]:
        findings = []
        with tempfile.TemporaryDirectory() as temp_dir:
            safe_filename = "source.cpp"
            file_path = os.path.join(temp_dir, safe_filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            try:
                result = subprocess.run(
                    ["clang-tidy", safe_filename, "--", "-std=c++17"],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout + result.stderr
                findings.extend(self._parse_clang_output(output, filename))
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
        return findings

    def _parse_clang_output(self, output: str, filename: str) -> List[Finding]:
        findings = []
        pattern = re.compile(r"source\.cpp:(\d+):(\d+):\s+(warning|error):\s+(.+?)(?:\s+\[(.*?)\])?$")
        for line in output.splitlines():
            m = pattern.search(line.strip())
            if m:
                line_no = int(m.group(1))
                diag_type = m.group(3)
                message = m.group(4)
                check_name = m.group(5) or "clang-tidy"
                
                category = Category.correctness
                lower_msg = (message + " " + check_name).lower()
                if any(k in lower_msg for k in ["bound", "buffer", "overflow", "memory", "null"]):
                    category = Category.memory_safety
                elif any(k in lower_msg for k in ["security", "cert-", "insecure"]):
                    category = Category.security
                elif "performance" in lower_msg:
                    category = Category.performance
                
                severity = Severity.high if diag_type == "error" else Severity.medium

                findings.append(Finding(
                    id=f"clang_{uuid.uuid4().hex[:8]}",
                    title=f"Clang diagnostic: {check_name}",
                    category=category,
                    severity=severity,
                    confidence=0.95,
                    file=filename,
                    start_line=line_no,
                    end_line=line_no,
                    source="clang_tidy",
                    evidence=message,
                    explanation=f"Clang-tidy reported {diag_type} in check '{check_name}'.",
                    suggestion="Address compiler diagnostic according to C++ standards.",
                    autofix=None
                ))
        return findings

    def _run_gcc_analyzer(self, code: str, filename: str) -> List[Finding]:
        findings = []
        with tempfile.TemporaryDirectory() as temp_dir:
            safe_filename = "source.cpp"
            obj_filename = "source.o"
            file_path = os.path.join(temp_dir, safe_filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            try:
                result = subprocess.run(
                    [
                        "g++",
                        "-O2",
                        "-Wall",
                        "-Wextra",
                        "-Warray-bounds",
                        "-Wuninitialized",
                        "-c",
                        safe_filename,
                        "-o",
                        obj_filename
                    ],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stderr
                findings.extend(self._parse_gcc_output(output, filename))
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                pass
        return findings

    def _parse_gcc_output(self, output: str, filename: str) -> List[Finding]:
        findings = []
        pattern = re.compile(r"source\.cpp:(\d+):(?:\d+:)?\s+(warning|error):\s+(.+?)(?:\s+\[-(W.*?)\])?$")
        for line in output.splitlines():
            m = pattern.search(line.strip())
            if m:
                line_no = int(m.group(1))
                diag_type = m.group(2)
                message = m.group(3)
                flag = m.group(4) or ""
                
                # Filter out benign unused variable warning if array bounds / uninitialized is primary
                if flag == "Wunused-but-set-variable":
                    continue

                category = Category.correctness
                severity = Severity.medium
                if "array-bounds" in flag or "out-of-bounds" in message:
                    category = Category.memory_safety
                    severity = Severity.high
                elif "uninitialized" in flag or "uninitialized" in message:
                    category = Category.correctness
                    severity = Severity.high
                elif "format" in flag:
                    category = Category.security
                    severity = Severity.high

                findings.append(Finding(
                    id=f"gcc_{uuid.uuid4().hex[:8]}",
                    title=f"Compiler diagnostic: {flag or diag_type}",
                    category=category,
                    severity=severity,
                    confidence=0.95,
                    file=filename,
                    start_line=line_no,
                    end_line=line_no,
                    source="gcc_compiler",
                    evidence=message,
                    explanation=f"GCC issued warning/error with flag -{flag} during compilation.",
                    suggestion="Fix diagnostic to prevent undefined behavior and build warnings.",
                    autofix=None
                ))
        return findings

    def _run_pattern_checks(self, code: str, filename: str) -> List[Finding]:
        findings = []
        lines = code.splitlines()

        # 1. Array declaration and out-of-bounds indexing
        arr_decl_pat = re.compile(
            r"\b(?:int|char|float|double|long|short|unsigned|uint\w*|size_t|bool)\s+([a-zA-Z_]\w*)\s*\[\s*(\d+)\s*\]"
        )
        arrays = {}
        for m in arr_decl_pat.finditer(code):
            name = m.group(1)
            size = int(m.group(2))
            decl_start = m.start(1)
            arrays[name] = (size, decl_start)

        for name, (size, decl_start) in arrays.items():
            idx_pat = re.compile(r"\b" + re.escape(name) + r"\s*\[\s*(\d+)\s*\]")
            for im in idx_pat.finditer(code):
                idx = int(im.group(1))
                line_no = code[:im.start()].count("\n") + 1
                if im.start() != decl_start and idx >= size:
                    findings.append(Finding(
                        id=f"bounds_{uuid.uuid4().hex[:8]}",
                        title=f"Array index out of bounds on '{name}'",
                        category=Category.memory_safety,
                        severity=Severity.critical if idx >= size * 2 else Severity.high,
                        confidence=0.98,
                        file=filename,
                        start_line=line_no,
                        end_line=line_no,
                        source="static_analyzer",
                        evidence=f"Array '{name}' has declared size {size} (indices 0..{size-1}), but is accessed with index {idx}.",
                        explanation="Array index out of bounds causes undefined behavior, memory corruption, and potential buffer overflow security vulnerabilities.",
                        suggestion=f"Ensure the index is within [0, {size - 1}], or use std::array/std::vector with .at({idx}) for bounds checked access.",
                        autofix=f"// Verify index < {size} before access: {name}[{idx}]"
                    ))

        # 2. Uninitialized variable detection
        uninit_decl_pat = re.compile(
            r"\b(int|float|double|char|long|short|size_t)\s+([a-zA-Z_]\w*)\s*;"
        )
        for m in uninit_decl_pat.finditer(code):
            var_type = m.group(1)
            var_name = m.group(2)
            decl_line = code[:m.start()].count("\n") + 1

            for idx, line in enumerate(lines[decl_line:], start=decl_line + 1):
                clean_line = re.sub(r"//.*", "", line)
                # If variable is assigned, stop checking
                if re.search(r"\b" + re.escape(var_name) + r"\s*=[^=]", clean_line):
                    break
                # If variable is passed as non-const ref or address-of, could be initialized
                if re.search(r"&\s*" + re.escape(var_name) + r"\b", clean_line):
                    break
                # If variable is read in expression
                if re.search(r"\b" + re.escape(var_name) + r"\b", clean_line):
                    findings.append(Finding(
                        id=f"uninit_{uuid.uuid4().hex[:8]}",
                        title=f"Use of uninitialized variable '{var_name}'",
                        category=Category.correctness,
                        severity=Severity.high,
                        confidence=0.92,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="static_analyzer",
                        evidence=f"Variable '{var_name}' is declared at line {decl_line} without initialization and read at line {idx}.",
                        explanation="Reading uninitialized primitive variables causes undefined behavior, non-deterministic values, and potential logic bugs.",
                        suggestion=f"Initialize '{var_name}' upon declaration: '{var_type} {var_name} = 0;'.",
                        autofix=f"{var_type} {var_name} = 0;"
                    ))
                    break

        # 3. Unsafe C functions (gets, strcpy, sprintf, etc.)
        unsafe_funcs = {
            "gets": ("gets() does not check buffer limits and is prone to buffer overflows. Removed in C++14.", Severity.critical),
            "strcpy": ("strcpy() does not check target buffer size. Use strncpy or std::string instead.", Severity.high),
            "strcat": ("strcat() can overflow destination buffers. Use std::string or strncat.", Severity.high),
            "sprintf": ("sprintf() does not perform bounds checking. Use snprintf or std::ostringstream.", Severity.high),
            "system": ("system() can lead to command injection if arguments are constructed from untrusted data.", Severity.high)
        }
        for fn_name, (expl, sev) in unsafe_funcs.items():
            pat = re.compile(r"\b" + fn_name + r"\s*\(")
            for idx, line in enumerate(lines, start=1):
                clean_line = re.sub(r"//.*", "", line)
                if pat.search(clean_line):
                    findings.append(Finding(
                        id=f"unsafe_{uuid.uuid4().hex[:8]}",
                        title=f"Use of unsafe function '{fn_name}'",
                        category=Category.security,
                        severity=sev,
                        confidence=0.95,
                        file=filename,
                        start_line=idx,
                        end_line=idx,
                        source="static_analyzer",
                        evidence=f"Call to '{fn_name}()' at line {idx}.",
                        explanation=expl,
                        suggestion=f"Replace '{fn_name}' with safe modern C++ alternatives.",
                        autofix=None
                    ))

        # 4. Raw pointer new without delete check
        has_new = any(re.search(r"\bnew\s+\w+", line) for line in lines)
        has_delete = any(re.search(r"\bdelete\b", line) for line in lines)
        if has_new and not has_delete:
            findings.append(Finding(
                id=f"leak_{uuid.uuid4().hex[:8]}",
                title="Potential memory leak (raw new without delete)",
                category=Category.memory_safety,
                severity=Severity.medium,
                confidence=0.85,
                file=filename,
                start_line=1,
                end_line=len(lines),
                source="static_analyzer",
                evidence="Found 'new' allocation without corresponding 'delete' expression.",
                explanation="Allocating heap memory without freeing it causes resource leaks.",
                suggestion="Prefer smart pointers (std::unique_ptr, std::shared_ptr) or RAII containers (std::vector).",
                autofix=None
            ))

        return findings
