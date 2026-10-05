"""Context cache shim over the query cache (separate namespace)."""
from app.cache import query_cache as _q


def make_key(*a, **k) -> str:
    return "ctx:" + _q.make_key(*a, **k)[2:]


get = _q.get
put = _q.put
