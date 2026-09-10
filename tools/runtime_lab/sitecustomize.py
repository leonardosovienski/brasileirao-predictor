"""Python otherwise swallows sitecustomize failures; abort an unguarded lab."""

import os

try:
    import lab_guard  # noqa: F401
except BaseException:
    os._exit(70)
