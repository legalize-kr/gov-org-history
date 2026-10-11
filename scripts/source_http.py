"""Read public source endpoints with bounded retries for transient failures."""

import time
from http.client import IncompleteRead, RemoteDisconnected
from urllib import error, request


def read_source(req: request.Request) -> bytes:
    for attempt in range(4):
        try:
            with request.urlopen(req, timeout=30) as response:
                return response.read()
        except error.HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (error.URLError, TimeoutError, ConnectionError, IncompleteRead, RemoteDisconnected):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)
    raise AssertionError("unreachable")
