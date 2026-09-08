"""Cross-process test entry: actual daemon with explicit synthetic boot params.

Only the database loader is replaced. Redis protocol, polling, numerical grid,
fair-odds generation and process lifecycle are the application's actual code.
"""

import asyncio
import os
from urllib.parse import urlparse

from brasileirao_predictor import kernel_daemon

url = os.environ['LINEUP_E2E_REDIS_URL']
parsed = urlparse(url)
if (parsed.hostname, parsed.port, parsed.path) != ('127.0.0.1', 26380, '/13'):
    raise RuntimeError('isolated cross-process Redis endpoint required')
kernel_daemon._load_params = lambda _: (0.2, 1.0, 0.1, 0.0, 0.0, 6)
asyncio.run(kernel_daemon._run_daemon('SYNTHETIC_NO_DATABASE_ACCESS', url))
