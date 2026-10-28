import re

class CodeRedactor:
    """
    Redacts sensitive credentials, tokens, passwords, and private keys
    before sending source code to external LLM providers.
    """
    
    # Common variable assignments containing sensitive strings
    ASSIGNMENT_PATTERN = re.compile(
        r"(?i)\b(api_key|apikey|secret|password|passwd|token|auth|access_key|private_key)"
        r"(\s*[:=]\s*)['\"]([^'\"]+)['\"]"
    )
    
    # Specific known token formats
    GH_TOKEN_PATTERN = re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}")
    AWS_KEY_PATTERN = re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}")
    BEARER_PATTERN = re.compile(r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})")
    PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")

    def redact(self, code: str) -> str:
        if not code:
            return code
            
        redacted = code
        
        # Redact private key blocks
        redacted = self.PRIVATE_KEY_PATTERN.sub("-----BEGIN PRIVATE KEY-----\nREDACTED_KEY_DATA\n-----END PRIVATE KEY-----", redacted)
        
        # Redact known credential assignments
        redacted = self.ASSIGNMENT_PATTERN.sub(r"\1\2'REDACTED_BY_CODESENTINEL'", redacted)
        
        # Redact standalone tokens
        redacted = self.GH_TOKEN_PATTERN.sub("ghp_REDACTED_TOKEN", redacted)
        redacted = self.AWS_KEY_PATTERN.sub("AKIAREDACTEDAWSKEY", redacted)
        redacted = self.BEARER_PATTERN.sub("Bearer REDACTED_TOKEN", redacted)
        
        return redacted
