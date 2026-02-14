"""
Custom Uvicorn worker that forces the asyncio event loop.

uvloop 0.21 + Python 3.13 causes a deadlock where the server
accepts TCP connections but never processes HTTP requests.
This worker ensures asyncio is always used.
"""
from uvicorn.workers import UvicornWorker


class AsyncioUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        **UvicornWorker.CONFIG_KWARGS,
        "loop": "asyncio",
    }
