"""Verify the specific boundary needed by the scoped test runner."""
import asyncio
import socket
import sqlite3
from pathlib import Path

import pytest


def test_asyncio_internal_socketpair_remains_usable():
    async def sample():
        return 7
    assert asyncio.run(sample()) == 7


def test_external_connection_is_still_blocked():
    with socket.socket() as channel:
        with pytest.raises(PermissionError, match='network_or_subprocess_forbidden'):
            channel.connect(('127.0.0.1', 6379))


def test_operational_sqlite_is_still_blocked():
    with pytest.raises(PermissionError, match='only_synthetic_sqlite'):
        sqlite3.connect('C:/BRASILEIRAO/brasileirao-predictor/data/matches.db')


def test_write_outside_output_is_still_blocked():
    with pytest.raises(PermissionError, match='write_outside_test_output'):
        Path('C:/BRASILEIRAO/work/revisao-integral-2026-09-09/forbidden-test-write.txt').write_text('forbidden')
