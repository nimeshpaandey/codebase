from app.analyzers.clang_tidy import ClangTidyAnalyzer
from app.schemas.finding import Category, Severity

def test_clang_tidy_analyzer_detects_bounds_and_uninit():
    analyzer = ClangTidyAnalyzer()
    code = """#include <iostream>

int main() {
    int arr[5];
    arr[10] = 50; 
    
    int uninit_val;
    std::cout << uninit_val << std::endl;

    return 0;
}"""
    findings = analyzer.analyze(code, "bad_code.cpp")
    categories = [f.category for f in findings]
    assert Category.memory_safety in categories
    assert Category.correctness in categories

def test_clang_tidy_analyzer_detects_insecure_functions():
    analyzer = ClangTidyAnalyzer()
    code = """
    #include <stdio.h>
    void test() {
        char buf[10];
        gets(buf);
    }
    """
    findings = analyzer.analyze(code, "insecure.cpp")
    security_findings = [f for f in findings if f.category == Category.security]
    assert len(security_findings) >= 1
    assert security_findings[0].severity == Severity.critical
