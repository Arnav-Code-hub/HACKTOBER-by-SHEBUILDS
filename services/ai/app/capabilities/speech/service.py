"""Speech-to-text for voice reports.

    QUEUED — slow and/or expensive. The API enqueues it onto the worker;
    it must never block a citizen's request.

Prompts live in prompts/ as versioned files, never as inline strings —
they are reviewed like code because they change behaviour like code.
Every model output that crosses back into the domain is validated against
the schema below before the API is allowed to trust it.
"""

# TODO(speech): implement.
