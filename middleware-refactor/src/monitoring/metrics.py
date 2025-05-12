# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram
from functools import wraps
import time

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

def track_request_time(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(
                method=func.__name__,
                endpoint=func.__name__,
                status='success'
            ).inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(
                method=func.__name__,
                endpoint=func.__name__,
                status='error'
            ).inc()
            raise e
        finally:
            REQUEST_LATENCY.labels(
                method=func.__name__,
                endpoint=func.__name__
            ).observe(time.time() - start_time)
    return wrapper