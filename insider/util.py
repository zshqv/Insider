import os
import re

_SECRET_PATTERNS = [
    re.compile(r"https://(?:discord(?:app)?\.com)/api/webhooks/\S+"),
    re.compile(r"https://script\.google(?:usercontent)?\.com/macros/\S+"),
]


def redact(text, *secrets):
    """Strip webhook URLs, the Apps Script URL and other secrets from text before logging."""
    text = str(text)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "<redacted>")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("<redacted-url>", text)
    return text


def env(name):
    """Read an env var, tolerating stray quotes/brackets pasted into GitHub secrets."""
    value = os.environ.get(name, "")
    return value.strip("[]'\" \n\r\t") or None
