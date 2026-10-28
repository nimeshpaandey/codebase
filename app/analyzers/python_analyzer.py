import ast
import re
import uuid
from typing import List, Optional
from app.schemas.finding import Finding, Category, Severity

class PythonASTVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, code_lines: List[str]):
        self.filename = filename
        self.code_lines = code_lines
        self.findings: List[Finding] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 1. Mutable default arguments
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                type_name = "list" if isinstance(default, ast.List) else "dict" if isinstance(default, ast.Dict) else "set"
                self.findings.append(Finding(
                    id=f"py_mut_{uuid.uuid4().hex[:8]}",
                    title=f"Mutable default argument '{type_name}' in function '{node.name}'",
                    category=Category.correctness,
                    severity=Severity.high,
                    confidence=0.98,
                    file=self.filename,
                    start_line=default.lineno,
                    end_line=default.end_lineno or default.lineno,
                    source="python_ast",
                    evidence=f"def {node.name}(..., default={type_name})",
                    explanation=(
                        f"Default parameter values are evaluated once when the function is defined. "
                        f"A mutable default {type_name} is shared across all function calls, leading to subtle state-mutation bugs."
                    ),
                    suggestion=f"Use 'None' as default value and initialize inside function body: `arg=None; if arg is None: arg = {default.__class__.__name__.lower()}()`.",
                    autofix=None
                ))
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # 2. Bare except clause
        if node.type is None:
            self.findings.append(Finding(
                id=f"py_bare_exc_{uuid.uuid4().hex[:8]}",
                title="Bare 'except:' clause used",
                category=Category.reliability,
                severity=Severity.medium,
                confidence=0.95,
                file=self.filename,
                start_line=node.lineno,
                end_line=node.lineno,
                source="python_ast",
                evidence="except:",
                explanation=(
                    "A bare 'except:' catches all exceptions, including SystemExit and KeyboardInterrupt, "
                    "making graceful shutdown and debugging difficult."
                ),
                suggestion="Catch explicit exceptions like 'except Exception:' or specific error classes.",
                autofix="except Exception as e:"
            ))
        
        # 3. Empty exception handler with pass
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append(Finding(
                id=f"py_empty_exc_{uuid.uuid4().hex[:8]}",
                title="Empty exception handler silently suppressing error",
                category=Category.maintainability,
                severity=Severity.medium,
                confidence=0.90,
                file=self.filename,
                start_line=node.lineno,
                end_line=node.body[0].lineno,
                source="python_ast",
                evidence="except ...: pass",
                explanation="Silently swallowing exceptions hides errors and makes debugging production failures nearly impossible.",
                suggestion="Log the exception or handle the error condition gracefully.",
                autofix=None
            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 4. Insecure functions (eval, exec)
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in ("eval", "exec"):
            self.findings.append(Finding(
                id=f"py_sec_{uuid.uuid4().hex[:8]}",
                title=f"Critical Security Risk: Use of '{func_name}()'",
                category=Category.security,
                severity=Severity.critical,
                confidence=0.98,
                file=self.filename,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                source="python_ast",
                evidence=f"{func_name}(...)",
                explanation=f"'{func_name}()' dynamically evaluates untrusted strings as Python code, enabling remote code execution (RCE).",
                suggestion=f"Avoid '{func_name}()'. Use 'ast.literal_eval()' for safe data parsing or specific parsers (e.g., json).",
                autofix="ast.literal_eval(...)" if func_name == "eval" else None
            ))
            
        elif func_name in ("system", "popen"):
            # Check os.system or os.popen
            self.findings.append(Finding(
                id=f"py_cmd_{uuid.uuid4().hex[:8]}",
                title=f"Potential command injection risk in '{func_name}()'",
                category=Category.security,
                severity=Severity.high,
                confidence=0.92,
                file=self.filename,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                source="python_ast",
                evidence=f"os.{func_name}(...)",
                explanation=f"Calling shell execution functions like '{func_name}()' without sanitized argument arrays can lead to command injection.",
                suggestion="Use 'subprocess.run([cmd, arg1, arg2], check=True)' with shell=False.",
                autofix=None
            ))

        # 5. Check subprocess with shell=True
        if func_name in ("run", "Popen", "call", "check_output"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.findings.append(Finding(
                        id=f"py_shell_{uuid.uuid4().hex[:8]}",
                        title="Subprocess execution with 'shell=True'",
                        category=Category.security,
                        severity=Severity.high,
                        confidence=0.95,
                        file=self.filename,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        source="python_ast",
                        evidence=f"subprocess.{func_name}(..., shell=True)",
                        explanation="Enabling shell=True passes strings directly to the system shell, exposing the application to shell injection.",
                        suggestion="Pass arguments as a list of strings and set 'shell=False'.",
                        autofix=None
                    ))
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        # 6. Comparison to None with == or !=
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(comparator, ast.Constant) and comparator.value is None:
                if isinstance(op, (ast.Eq, ast.NotEq)):
                    op_str = "==" if isinstance(op, ast.Eq) else "!="
                    rec_str = "is None" if isinstance(op, ast.Eq) else "is not None"
                    self.findings.append(Finding(
                        id=f"py_cmp_{uuid.uuid4().hex[:8]}",
                        title=f"Comparison with None using '{op_str}' instead of identity operator",
                        category=Category.style,
                        severity=Severity.low,
                        confidence=0.96,
                        file=self.filename,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        source="python_ast",
                        evidence=f"x {op_str} None",
                        explanation="In Python (PEP 8), comparisons to singletons like None should always be done with 'is' or 'is not', never the equality operators.",
                        suggestion=f"Replace '{op_str} None' with '{rec_str}'.",
                        autofix=rec_str
                    ))
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # 7. Division by zero on literal constant
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.findings.append(Finding(
                    id=f"py_divzero_{uuid.uuid4().hex[:8]}",
                    title="Literal division by zero detected",
                    category=Category.correctness,
                    severity=Severity.high,
                    confidence=0.99,
                    file=self.filename,
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    source="python_ast",
                    evidence=f"... / 0 at line {node.lineno}",
                    explanation="Dividing or moduloing by literal constant zero raises ZeroDivisionError at runtime.",
                    suggestion="Verify divisor is non-zero before performing division.",
                    autofix=None
                ))
        self.generic_visit(node)


class PythonAnalyzer:
    """
    Static analyzer for Python source code using native AST inspection,
    syntax validation, and security pattern detection.
    """

    def analyze(self, code: str, filename: str = "main.py") -> List[Finding]:
        findings: List[Finding] = []
        code_lines = code.splitlines()

        # 1. Syntax check via AST compilation
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError as e:
            findings.append(Finding(
                id=f"py_syn_{uuid.uuid4().hex[:8]}",
                title=f"Python SyntaxError: {e.msg}",
                category=Category.correctness,
                severity=Severity.critical,
                confidence=1.0,
                file=filename,
                start_line=e.lineno or 1,
                end_line=e.lineno or 1,
                source="python_compiler",
                evidence=e.text.strip() if e.text else str(e),
                explanation=f"Source code has a syntax error and cannot be compiled: {e.msg}",
                suggestion="Correct syntax according to Python specifications.",
                autofix=None
            ))
            return findings

        # 2. Walk AST for semantic and pattern defects
        visitor = PythonASTVisitor(filename, code_lines)
        visitor.visit(tree)
        findings.extend(visitor.findings)

        # 3. Additional regex checks (e.g. SQL injection in execute())
        sql_pattern = re.compile(r"""\b(?:execute|cursor\.execute)\s*\(\s*(?:f['\"].*?\{.+?\}.*?['\"]|['\"].*?%s.*?['\"]\s*%)""", re.IGNORECASE)
        for idx, line in enumerate(code_lines, start=1):
            if sql_pattern.search(line):
                findings.append(Finding(
                    id=f"py_sqli_{uuid.uuid4().hex[:8]}",
                    title="Potential SQL Injection via string formatting",
                    category=Category.security,
                    severity=Severity.critical,
                    confidence=0.93,
                    file=filename,
                    start_line=idx,
                    end_line=idx,
                    source="python_analyzer",
                    evidence=line.strip(),
                    explanation="Dynamically formatting variables into SQL queries via f-strings or %-formatting allows SQL injection attacks.",
                    suggestion="Use parameterized queries with placeholder tuples: `cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))`.",
                    autofix=None
                ))

        # 4. Insecure unpinned yaml.load or pickle.loads
        for idx, line in enumerate(code_lines, start=1):
            if re.search(r"\byaml\.load\s*\([^)]*Loader\s*=\s*(?:yaml\.)?Loader", line) or re.search(r"\byaml\.load\s*\([^,)]+\)", line):
                findings.append(Finding(
                    id=f"py_yaml_{uuid.uuid4().hex[:8]}",
                    title="Unsafe YAML loading with yaml.load",
                    category=Category.security,
                    severity=Severity.high,
                    confidence=0.92,
                    file=filename,
                    start_line=idx,
                    end_line=idx,
                    source="python_analyzer",
                    evidence=line.strip(),
                    explanation="yaml.load() without SafeLoader can deserialize arbitrary Python objects and execute arbitrary code.",
                    suggestion="Use `yaml.safe_load(...)` instead.",
                    autofix="yaml.safe_load(...)"
                ))

        return findings
