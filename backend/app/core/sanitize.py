"""
Input sanitization utilities.
Prevents stored XSS via filenames, descriptions, and user-provided text.
"""
import html
import re

# Allowed filename characters (alphanumeric, dash, underscore, dot, space)
_SAFE_FILENAME_RE = re.compile(r"[^\w\s\-.]", re.UNICODE)

# Max field lengths
MAX_FILENAME_LENGTH = 255
MAX_DESCRIPTION_LENGTH = 50_000
MAX_TITLE_LENGTH = 255


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a user-uploaded filename.
    Strips path components, HTML entities, and dangerous characters.

    Args:
        filename: Raw filename from upload

    Returns:
        Safe filename string
    """
    if not filename:
        return "upload"

    # Strip path separators (prevents path traversal)
    filename = filename.replace("/", "_").replace("\\", "_")

    # HTML-escape any entities
    filename = html.escape(filename, quote=True)

    # Remove characters not in the safe set
    filename = _SAFE_FILENAME_RE.sub("", filename)

    # Truncate
    filename = filename[:MAX_FILENAME_LENGTH].strip()

    return filename or "upload"


def sanitize_text(text: str, max_length: int = MAX_DESCRIPTION_LENGTH) -> str:
    """
    Sanitize user-provided text content.
    Strips script tags and HTML but preserves readable content.

    Args:
        text: Raw text input
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Strip HTML tags (basic XSS prevention)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities that might be double-encoded
    text = html.unescape(text)

    # Remove null bytes
    text = text.replace("\x00", "")

    # Truncate
    return text[:max_length]


def sanitize_title(title: str) -> str:
    """Sanitize a title field."""
    return sanitize_text(title, max_length=MAX_TITLE_LENGTH).strip()
