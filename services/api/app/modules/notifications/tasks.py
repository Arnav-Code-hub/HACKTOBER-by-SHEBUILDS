"""Background jobs for notifications, executed by the ARQ worker.

The worker runs from the same image as the API (app/worker.py), so these
import module internals directly — no serialisation boundary, no duplicate
dependency set. Slow or expensive work belongs here, not in a request.
"""

# TODO(notifications): tasks.
