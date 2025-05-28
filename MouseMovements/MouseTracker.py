import pygame
import json
import time

class PygameMouseTracker:
    def __init__(self, filepath):
        self.filepath = filepath
        self.events = []
        self.start_time = None

    def _timestamp(self):
        return time.time() - self.start_time if self.start_time else 0

    def log_event(self, event_type, data):
        self.events.append({
            "time": self._timestamp(),
            "type": event_type,
            "data": data
        })

    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.events, f, indent=2)

    def load(self):
        with open(self.filepath, 'r') as f:
            self.events = json.load(f)
        return self.events
    
    # mouse_recorder.py

class MouseRecorder:
    """Record pygame mouse positions (or any custom events) with timestamps."""
    def __init__(self, path):
        self.path = path          # log file (JSON-lines)
        self.trial_id = None
        self.trial_start = None
        self.file = open(self.path, "a", buffering=1)   # line-buffered

    def _ts(self) -> float:
        return time.time() - self.trial_start           # seconds since trial start

    # ---------- Trial control -------------------------------------------------
    def start_trial(self, trial_id: int):
        self.trial_id = trial_id
        self.trial_start = time.time()
        self._write("trial_start", {})                  # mark the boundary

    def stop_trial(self):
        self._write("trial_end", {})
        self.trial_id, self.trial_start = None, None

    # ---------- Per-frame update ---------------------------------------------
    def update(self):
        if self.trial_start is None:
            return  # not recording right now
        x, y = pygame.mouse.get_pos()
        self._write("move", {"x": x, "y": y})

    # ---------- External event hook ------------------------------------------
    def log_event(self, event_type: str, data: dict):
        """Call this from any part of the program when something notable happens."""
        if self.trial_start is not None:
            self._write(event_type, data)

    # ---------- Internal writer ----------------------------------------------
    def _write(self, etype: str, data: dict):
        entry = {
            "trial": self.trial_id,
            "time": self._ts(),
            "type": etype,
            "data": data,
        }
        print(json.dumps(entry), file=self.file)        # one JSON object per line

    def close(self):
        self.file.close()
