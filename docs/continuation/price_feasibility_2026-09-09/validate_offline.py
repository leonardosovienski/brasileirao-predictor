"""Run only price arithmetic and scanner synthetic tests with containment."""

import os
import sys
from pathlib import Path


def main():
    repository = Path(sys.argv[1]).resolve()
    work = Path(sys.argv[2]).resolve()
    if work.is_relative_to(repository):
        raise ValueError("test_work_must_be_outside_repository")
    work.mkdir(parents=True, exist_ok=True)
    keep = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}
    for name in list(os.environ):
        if name.upper() not in keep:
            del os.environ[name]
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["TEMP"] = os.environ["TMP"] = str(work)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repository))

    def guard(event, args):
        if event.startswith(("socket.", "sqlite3.", "subprocess.", "os.system")):
            raise PermissionError("network_database_subprocess_forbidden")
        if event == "open" and isinstance(args[0], str | bytes | os.PathLike):
            path = Path(os.fsdecode(args[0])).resolve()
            mode, flags = args[1] or "", args[2] or 0
            writing = any(char in mode for char in "wax+") or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)
            if writing and not path.is_relative_to(work):
                raise PermissionError("write_outside_test_work_forbidden")
            if path.is_relative_to(repository / "data") or path.name == ".env":
                raise PermissionError("operational_data_forbidden")

    sys.addaudithook(guard)
    import pytest

    raise SystemExit(
        pytest.main(
            [
                str(repository / "tests/test_price_hurdle.py"),
                str(repository / "tests/test_price_strength_quotes.py"),
                "-q",
                "-p",
                "no:cacheprovider",
                "-o",
                f"log_file={work / 'pytest.log'}",
                "--basetemp",
                str(work / "tmp"),
                "--junitxml",
                str(work / "junit.xml"),
            ]
        )
    )


if __name__ == "__main__":
    main()
