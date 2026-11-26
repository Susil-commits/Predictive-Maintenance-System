"""
backend/limiter.py
==================
Shared SlowAPI limiter instance for PMS endpoints.
Uses Redis distributed storage when REDIS_URL is configured and reachable,
falling back gracefully to process-local memory storage otherwise.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from .redis_client import get_redis_storage_uri

limiter = Limiter(key_func=get_remote_address, storage_uri=get_redis_storage_uri())
