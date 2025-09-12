# backoff.py
import random, time

def backoff(on_exceptions, tries=5, base=0.8, cap=8.0, jitter=0.5):
    def deco(fn):
        def wrapper(*args, **kwargs):
            t = 0
            for attempt in range(1, tries + 1):
                try:
                    return fn(*args, **kwargs)
                except on_exceptions as e:
                    if attempt == tries:
                        raise
                    sleep_for = min(cap, base * (2 ** (attempt - 1))) + random.uniform(0, jitter)
                    time.sleep(sleep_for)
            # should not reach
        return wrapper
    return deco
