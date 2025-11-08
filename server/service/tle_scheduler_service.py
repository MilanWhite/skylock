import threading
import time
from datetime import datetime, timedelta
import requests

from server.model.repository import ITleRepository

class TleSchedulerService:
    def __init__(self, repo: ITleRepository, tle_group: str, interval_seconds: int = 3600):
        self.repo = repo
        self.tle_group = tle_group
        self.interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread = None
        self._last_fetch_time = None

    def _has_internet(self, test_url="https://celestrak.org", timeout=5):
        try:
            requests.get(test_url, timeout=timeout)
            return True
        except Exception:
            return False

    def _fetch_and_store(self):
        try:
            text = self.repo.fetch_tle_group(self.tle_group)
            tles = self.repo.parse_tles(text)
            self.repo.upsert_tles(tles, source=f'celestrak:{self.tle_group}')
            self._last_fetch_time = datetime.now()
            print(f"[TleSchedulerService] Fetched and stored TLEs for group {self.tle_group} at {self._last_fetch_time}")
        except Exception as e:
            print(f"[TleSchedulerService] Error fetching TLEs: {e}")

    def _run(self):
        while not self._stop_event.is_set():
            now = datetime.now()
            # If never fetched or it's been more than interval, try to fetch
            if (self._last_fetch_time is None or
                (now - self._last_fetch_time) >= timedelta(seconds=self.interval)):
                if self._has_internet():
                    self._fetch_and_store()
                else:
                    print("[TleSchedulerService] No internet connection. Will retry soon.")
            # Sleep in short intervals to allow quick recovery after connection returns
            time.sleep(60)

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            print("[TleSchedulerService] Scheduler started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            print("[TleSchedulerService] Scheduler stopped.")
