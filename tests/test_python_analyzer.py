from app.analyzers.python_analyzer import PythonAnalyzer
from app.schemas.finding import Category, Severity

def test_python_syntax_error():
    analyzer = PythonAnalyzer()
    code = "def broken_func(:\n    pass"
    findings = analyzer.analyze(code, "broken.py")
    assert len(findings) == 1
    assert findings[0].category == Category.correctness
    assert findings[0].severity == Severity.critical
    assert "SyntaxError" in findings[0].title

def test_python_mutable_defaults():
    analyzer = PythonAnalyzer()
    code = "def add_item(item, items=[]):\n    items.append(item)\n    return items"
    findings = analyzer.analyze(code, "mut.py")
    assert any(f.category == Category.correctness and "Mutable default argument" in f.title for f in findings)

def test_python_insecure_calls():
    analyzer = PythonAnalyzer()
    code = """
import os
import subprocess

def run_user_code(user_input):
    eval(user_input)
    os.system("ls " + user_input)
    subprocess.Popen(user_input, shell=True)
"""
    findings = analyzer.analyze(code, "sec.py")
    security_findings = [f for f in findings if f.category == Category.security]
    assert len(security_findings) >= 3

def test_python_none_comparison_and_bare_except():
    analyzer = PythonAnalyzer()
    code = """
def check(val):
    try:
        x = 10 / 0
    except:
        pass
    if val == None:
        return True
    return False
"""
    findings = analyzer.analyze(code, "rel.py")
    categories = [f.category for f in findings]
    assert Category.reliability in categories  # Bare except
    assert Category.style in categories        # == None
    assert Category.correctness in categories    # Division by zero

def test_python_clean_code():
    analyzer = PythonAnalyzer()
    code = """
from typing import List, Optional

def safe_add(item: int, target: Optional[List[int]] = None) -> List[int]:
    res = list(target) if target is not None else []
    res.append(item)
    return res
"""
    findings = analyzer.analyze(code, "clean.py")
    assert len(findings) == 0
