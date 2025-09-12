import random, time

def backoff(on_exceptions, tries=7, base=1.2, cap=12.0, jitter=1.0):
    def deco(fn):
        def wrapper(*args, **kwargs):
            for attempt in range(1, tries + 1):
                try:
                    return fn(*args, **kwargs)
                except on_exceptions:
                    if attempt == tries: raise
                    sleep_for = min(cap, base * (2 ** (attempt - 1))) + random.uniform(0, jitter)
                    time.sleep(sleep_for)
        return wrapper
    return deco