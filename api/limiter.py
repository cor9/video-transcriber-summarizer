import threading, time, random

# At most 1 active fetch; queue others
_fetch_gate = threading.BoundedSemaphore(1)

class fetch_slot:
    def __enter__(self):
        _fetch_gate.acquire()
        # tiny random delay to de-sync bursts
        time.sleep(0.3 + random.random()*0.4)
        return self
    def __exit__(self, exc_type, exc, tb):
        _fetch_gate.release()
