from typing import Union
from app.analyzers.clang_tidy import ClangTidyAnalyzer
from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.java_analyzer import JavaAnalyzer

def get_analyzer_for_language(language: str):
    """
    Returns the appropriate static analyzer instance for the given programming language.
    """
    lang = (language or "cpp").lower().strip()
    if lang in ("python", "py"):
        return PythonAnalyzer()
    elif lang in ("java",):
        return JavaAnalyzer()
    else:  # "cpp", "c++", default
        return ClangTidyAnalyzer()

__all__ = [
    "ClangTidyAnalyzer",
    "PythonAnalyzer",
    "JavaAnalyzer",
    "get_analyzer_for_language"
]
