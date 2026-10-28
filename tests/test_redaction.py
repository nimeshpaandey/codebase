from app.security.redaction import CodeRedactor

def test_code_redactor_secrets():
    redactor = CodeRedactor()
    code = """
    const char* api_key = "AIzaSyD-123456789";
    std::string secret = "SuperSecretPass123";
    std::string token = 'secret_token_abc';
    int normal_var = 42;
    """
    redacted = redactor.redact(code)
    assert "AIzaSyD-123456789" not in redacted
    assert "SuperSecretPass123" not in redacted
    assert "secret_token_abc" not in redacted
    assert "REDACTED_BY_CODESENTINEL" in redacted
    assert "normal_var = 42" in redacted

def test_code_redactor_tokens_and_keys():
    redactor = CodeRedactor()
    code = """
    // AWS Access Key
    char aws[] = "AKIAIOSFODNN7EXAMPLE";
    // GitHub token
    char gh[] = "ghp_1234567890abcdefghijklmnopqrstuvwxyz12";
    """
    redacted = redactor.redact(code)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz12" not in redacted
