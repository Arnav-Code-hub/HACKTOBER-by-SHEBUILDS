"""Business logic for rbac. THE PUBLIC FACE of this module.

Role assignment and permission introspection.

# Module boundary: other modules may import this file and schemas.py.
# They must NEVER import models.py or repository.py — see the import-linter
# contract in pyproject.toml. That rule is what makes this module extractable
# into its own service later without touching a single caller.
"""

# TODO(rbac): service functions.
