"""Rate limiter for MCP server tool invocations (M6 / G5).

Token-bucket algorithm, in-process, thread-safe. Sized for single-agent
private beta. Re-tune before public launch.

Usage:
    from borg.core.rate_limiter import check_rate_limit, RateLimitExceeded
    def borg_observe(...):
        check_rate_limit('borg_observe', agent_id=...)
        ...
"""
import time
import threading
from collections import defaultdict


class RateLimitExceeded(Exception):
    pass


_DEFAULT_LIMITS = {
    'borg_observe':  {'rate': 60,  'burst': 10},
    'borg_rate':     {'rate': 30,  'burst': 5},
    'borg_publish':  {'rate': 5,   'burst': 2},
    'borg_search':   {'rate': 30,  'burst': 5},
    'borg_suggest':  {'rate': 30,  'burst': 5},
    '_default':      {'rate': 30,  'burst': 5},
}

_buckets = defaultdict(lambda: {'tokens': 0.0, 'last_refill': 0.0})
_lock = threading.Lock()


def _refill(bucket, rate_per_min, burst):
    now = time.monotonic()
    if bucket['last_refill'] == 0.0:
        bucket['tokens'] = float(burst)
    else:
        elapsed = now - bucket['last_refill']
        bucket['tokens'] = min(
            float(burst),
            bucket['tokens'] + elapsed * (rate_per_min / 60.0)
        )
    bucket['last_refill'] = now


def check_rate_limit(tool_name, agent_id='anonymous', limits=None):
    """Consume one token. Raise RateLimitExceeded on exhaustion."""
    limits = limits or _DEFAULT_LIMITS
    cfg = limits.get(tool_name, limits['_default'])
    key = f'{tool_name}::{agent_id}'
    with _lock:
        bucket = _buckets[key]
        _refill(bucket, cfg['rate'], cfg['burst'])
        if bucket['tokens'] < 1.0:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {tool_name} by {agent_id}: "
                f"{cfg['rate']}/min, burst {cfg['burst']}"
            )
        bucket['tokens'] -= 1.0
    return True


def reset_bucket(tool_name, agent_id):
    """For tests and admin actions."""
    key = f'{tool_name}::{agent_id}'
    with _lock:
        if key in _buckets:
            del _buckets[key]
