# 🛡️ CodeSentinel

**CodeSentinel** is a multi-language AI-powered code review and static analysis agent supporting **C++**, **Python**, and **Java**. It combines deterministic compiler diagnostics (`clang-tidy`, `g++`, `javac`), AST & pattern-based static analysis, and semantic LLM reasoning (via Google Gemini with automatic intelligent local fallback) into a unified code quality and security pipeline.

---

## 🌟 Multi-Language Architecture & Capabilities

```
                  ┌─────────────────────────────────────────┐
                  │ Multi-Language Code Submission          │
                  │ (C++, Python, Java)                     │
                  └────────────────────┬────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
   [Language Static Analyzers]                        [Privacy Redaction Engine]
   • C++: clang-tidy, g++ -O2 -Wall,                  • Sanitizes API keys, secrets,
     bounds & uninitialized checks                      tokens, passwords, AWS keys,
   • Python: native AST visitor, compile(),             and private keys before LLM
     mutable defaults, eval/exec, bare except         └───────────────┬────────────────┘
   • Java: javac -Xlint:all linting,                                  ▼
     string '==' checks, NPE, resource leaks              [AI Semantic Reasoning]
            │                                             • Google Gemini (structured JSON)
            │                                             • Local multi-lang AI fallback
            └──────────────────────────┬──────────────────────────────┘
                                       ▼
                          [Finding Deduplicator]
                          • Merges overlapping findings
                          • Preserves multi-source provenance
                          • Aggregates confidence & actionable fixes
                                       │
                                       ▼
                           [SQLite Persistence Layer]
                           • Reviews & findings stored
                                       │
                                       ▼
                         [REST API & Web Dashboard]
```

### 1. Language-Specific Analyzers
- **C++**:
  - `clang-tidy` integration (when installed).
  - Native `g++ -O2 -Wall -Wextra -Warray-bounds -Wuninitialized` compiler diagnostics.
  - Deterministic AST/pattern checks: out-of-bounds array access, uninitialized variables, insecure C functions (`gets`, `strcpy`, `system`), memory leaks (`new` without `delete`).
- **Python**:
  - Native Python `ast` syntax parser & compiler diagnostics.
  - Detects mutable default parameter arguments (`def f(items=[])`).
  - Detects security risks (`eval()`, `exec()`, `os.system()`, `subprocess.Popen(..., shell=True)`, unsafe `yaml.load()`, `pickle.loads()`).
  - Detects reliability issues (bare `except:`, empty `except: pass`, literal division by zero).
  - Detects SQL injection formatting in query executions.
- **Java**:
  - `javac -Xlint:all` lint compiler diagnostics.
  - Detects string comparison using reference identity (`==` or `!=` instead of `.equals()`).
  - Detects array out-of-bounds on fixed-size arrays.
  - Detects potential `NullPointerException` (null assignment dereferenced without check).
  - Detects unclosed stream/file resources (`FileInputStream`, `Scanner`, `BufferedReader`).
  - Detects command injection (`Runtime.getRuntime().exec()`) and SQL injection in JDBC queries.

### 2. Privacy Redaction Engine
- Strips sensitive credentials (API keys, passwords, bearer tokens, AWS credentials, RSA/EC private keys) *before* submitting code to any external model.

### 3. Dual-Mode AI Reasoning (C++, Python, Java)
- **Google Gemini**: Uses Google Generative AI with strict JSON output schemas.
- **Intelligent Local AI Analyzer**: Automatically activates when `GOOGLE_API_KEY` is not provided or in offline environments, ensuring 100% functionality out of the box.

### 4. Interactive Web Dashboard
- Multi-language switcher with preset sample code for **C++**, **Python**, and **Java**.
- Check categories: Memory Safety, Correctness, Security, Reliability, Performance.
- Displays line numbers, severity tags, confidence metrics, evidence blocks, and actionable autofixes.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- `g++` (for C++ diagnostics)
- `javac` (for Java diagnostics, OpenJDK 17+)

### 2. Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Configuration variables:
```env
# Optional: Set your Gemini API key to enable cloud LLM analysis
GOOGLE_API_KEY=your_gemini_api_key_here

# LLM provider: "auto" (default), "gemini", or "mock"
LLM_PROVIDER=auto

# Model name when using Gemini
LLM_MODEL=gemini-1.5-flash

# GitHub Webhook HMAC Secret
GITHUB_WEBHOOK_SECRET=dummy_secret_for_local_test

# SQLite Database
DATABASE_PATH=data/codesentinel.db
```

---

## 🖥️ Running the Application

### Start the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive Web Dashboard**: [http://localhost:8000/](http://localhost:8000/)
- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 📊 Multi-Language Evaluation Benchmark

Run the automated evaluation benchmark across C++, Python, and Java:
```bash
python scripts/evaluate.py
```

Output:
```
==========================================
  Evaluation Report: CPP
==========================================
Total Findings Reported: 2
Expected Bugs Found (True Positives): 2 / 2
Precision: 1.00
Recall:    1.00
Reported Issues:
 - [correctness] Use of uninitialized variable 'uninit_val' (L10, Source: gcc_compiler, llm_agent, static_analyzer)
 - [memory_safety] Array index out of bounds on 'arr' (L6, Source: llm_agent, static_analyzer)

==========================================
  Evaluation Report: PYTHON
==========================================
Total Findings Reported: 3
Expected Bugs Found (True Positives): 3 / 3
Precision: 1.00
Recall:    1.00
Reported Issues:
 - [correctness] Mutable default argument 'list' in function 'add_item' (L4, Source: llm_agent, python_ast)
 - [security] Critical Security Risk: Use of 'eval()' (L11, Source: llm_agent, python_ast)
 - [reliability] Bare 'except:' clause used (L14, Source: llm_agent, python_ast)

==========================================
  Evaluation Report: JAVA
==========================================
Total Findings Reported: 3
Expected Bugs Found (True Positives): 3 / 3
Precision: 1.00
Recall:    1.00
Reported Issues:
 - [correctness] String comparison using reference equality ('==' or '!=') (L11, Source: java_analyzer, llm_agent)
 - [memory_safety] Array index out of bounds on 'numbers' (L7, Source: java_analyzer)
 - [security] Command execution via Runtime.getRuntime().exec() (L17, Source: java_analyzer, llm_agent)

==========================================
  MULTI-LANGUAGE BENCHMARK SUMMARY
==========================================
[PASSED] CPP      | Precision: 1.00 | Recall: 1.00 | Findings: 2
[PASSED] PYTHON   | Precision: 1.00 | Recall: 1.00 | Findings: 3
[PASSED] JAVA     | Precision: 1.00 | Recall: 1.00 | Findings: 3
```

You can also evaluate a single language:
```bash
python scripts/evaluate.py --lang python
python scripts/evaluate.py --lang java
python scripts/evaluate.py --lang cpp
```

---

## 🧪 Running the Test Suite

Run the full automated test suite with `pytest`:
```bash
pytest -v
```

All 27 tests cover:
- Schemas & validation rules
- Privacy redaction regexes
- Deduplication and provenance preservation
- C++ Clang & GCC static analyzers
- Python AST & security analyzers
- Java Javac & pattern analyzers
- SQLite database migrations and queries
- FastAPI REST endpoints & GitHub Webhook HMAC validation

---

## 📡 API Reference

### 1. `POST /api/reviews`
Submit C++, Python, or Java source code for review.

#### Python Example:
```json
{
  "language": "python",
  "filename": "main.py",
  "code": "def run(x=[]):\n    eval(x)\n    return x",
  "checks": ["correctness", "security", "reliability"]
}
```

#### Java Example:
```json
{
  "language": "java",
  "filename": "Main.java",
  "code": "public class Main { public static void main(String[] args) { String s = \"guest\"; if (s == \"admin\") {} } }",
  "checks": ["correctness", "security"]
}
```

Response:
```json
{
  "review_id": "rev_3bf98a719d21",
  "status": "completed",
  "findings": [
    {
      "id": "java_streq_714392",
      "title": "String comparison using reference equality ('==' or '!=')",
      "category": "correctness",
      "severity": "high",
      "confidence": 0.98,
      "file": "Main.java",
      "start_line": 1,
      "end_line": 1,
      "source": "java_analyzer, llm_agent",
      "evidence": "if (s == \"admin\")",
      "explanation": "In Java, '==' compares object memory references rather than string content values.",
      "suggestion": "Use '.equals()' or 'Objects.equals(a, b)' for value equality comparison.",
      "autofix": "\"admin\".equals(s)"
    }
  ]
}
```

### 2. `GET /api/reviews/{review_id}`
Retrieve past review results and findings by ID.

### 3. `GET /api/reviews?limit=20`
List recent code review records.

### 4. `POST /api/webhooks/github`
Handles GitHub webhook pull request events (`opened`, `synchronize`, `reopened`) verified using HMAC SHA-256 (`X-Hub-Signature-256`).
