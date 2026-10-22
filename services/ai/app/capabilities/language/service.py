"""Detect language, translate and transliterate.

    SYNCHRONOUS — the API calls this in a request path. Keep it fast.

Prompts live in prompts/ as versioned files, never as inline strings —
they are reviewed like code because they change behaviour like code.
Every model output that crosses back into the domain is validated against
the schema below before the API is allowed to trust it.
"""

# TODO(language): implement.
