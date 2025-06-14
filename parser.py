import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
from stimulus import Utils


class AscParser:
    """Parser for EDF2ASC *\*.asc* eye-tracking logs.

    The class extracts core metadata and splits the continuous sample stream
    into trials using the conventional *TRIALID* / *END* markers written by
    SR-Research EyeLink.

    It currently supports **two** common ways sample rate is expressed:

    1. Classic *MSG … SAMPLE_RATE <Hz>* line (older EyeLink firmware).
    2. Block header lines such as ``EVENTS … RATE 1000.00 …`` or
       ``SAMPLES … RATE 500.00 …`` (newer EDF2ASC default output).

    Extend or adapt the regular expressions below if your lab logs custom
    messages.
    """

    # ------------------------------------------------------------------
    # Regular expressions for message parsing
    # ------------------------------------------------------------------
    _RE_DISPLAY = re.compile(r"DISPLAY_COORDS\s+\d+\s+\d+\s+(\d+)\s+(\d+)")
    _RE_SR_MSG = re.compile(r"^MSG\s+\d+\s+SAMPLE_RATE\s+(\d+)")
    _RE_SR_BLOCK = re.compile(
        r"^(?:EVENTS|SAMPLES)\s+\S+\s+\S+\s+RATE\s+(\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    _RE_TRIAL_START = re.compile(r"^MSG\s+\d+\s+TRIALID\s+(\S+)")
    _RE_TRIAL_END = re.compile(r"^MSG\s+\d+\s+(?:END|STOP)")
    _RE_SAMPLE = re.compile(
        r"^(\d+)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)"
    )

    def __init__(self, filepath: str | Path):
        self.filepath: Path = Path(filepath)
        self.screen_width: Optional[int] = None
        self.screen_height: Optional[int] = None
        self.sample_rate: Optional[int] = None
        self.trials: Dict[str, List[Dict[str, float | int]]] = defaultdict(list)
        self._parse_file()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def get_screen_dims(self) -> Tuple[int | None, int | None]:
        """Return *(width, height)* of the recorded display in pixels."""
        return self.screen_width, self.screen_height

    def get_sample_rate(self) -> Optional[int]:
        """Nominal sampling rate in Hz (integer) or *None* if not found."""
        return self.sample_rate

    def list_trials(self) -> List[str]:
        """All trial identifiers in their original encounter order."""
        return list(self.trials.keys())

    def to_dataframe(self, trial_id: str) -> pd.DataFrame:
        """Return a *pandas.DataFrame* (indexed by time) for one trial."""
        if trial_id not in self.trials:
            raise KeyError(f"Trial '{trial_id}' not found.")
        df = pd.DataFrame(self.trials[trial_id])

        # Normalize x and y to screen dimensions using Utils
        df["x"] = df["x"] / self.screen_width * Utils.WIDTH if self.screen_width else df["x"]
        df["y"] = df["y"] / self.screen_height * Utils.HEIGHT if self.screen_height else df["y"]

        return df.set_index("time")

    def summary(self) -> dict:
        """Lightweight summary useful for sanity checks and logging."""
        return {
            "file": str(self.filepath),
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "sample_rate": self.sample_rate,
            "n_trials": len(self.trials),
        }
    
    def get_messages(self, trial_id: str) -> List[Tuple[int, str]]:
        """Return list of (timestamp, message) tuples for the trial."""
        messages = []
        with self.filepath.open("r", encoding="utf-8", errors="ignore") as fh:
            recording = False
            current_trial = None
            for line in fh:
                line = line.strip()
                if line.startswith("MSG"):
                    parts = line.split(None, 2)
                    if len(parts) < 3:
                        continue
                    ts, msg = int(parts[1]), parts[2]
                    if msg.startswith("TRIALID"):
                        current_trial = msg.split()[1]
                        recording = current_trial == str(trial_id)
                    elif msg.startswith(("END", "STOP")):
                        recording = False
                    elif recording:
                        messages.append((ts, msg))
        return messages
    
    # ------------------------------------------------------------------
    # Internal parsing routine
    # ------------------------------------------------------------------
    def _parse_file(self) -> None:
        current_trial: Optional[str] = None

        with self.filepath.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue

                # ------------------------------------------------------
                # Meta‑messages
                # ------------------------------------------------------
                if self.screen_width is None:
                    m = self._RE_DISPLAY.search(line)
                    if m:
                        self.screen_width = int(m.group(1))
                        self.screen_height = int(m.group(2))
                        continue

                if self.sample_rate is None:
                    m = self._RE_SR_MSG.match(line) or self._RE_SR_BLOCK.match(line)
                    if m:
                        # Round to nearest integer so "1000.00" ➜ 1000
                        self.sample_rate = int(round(float(m.group(1))))
                        continue

                # ------------------------------------------------------
                # Trial boundaries
                # ------------------------------------------------------
                m = self._RE_TRIAL_START.match(line)
                if m:
                    current_trial = m.group(1)
                    continue

                if self._RE_TRIAL_END.match(line):
                    current_trial = None
                    continue

                # ------------------------------------------------------
                # Continuous sample stream (within a trial only)
                # ------------------------------------------------------
                if current_trial is not None:
                    m = self._RE_SAMPLE.match(line)
                    if m:
                        ts, x, y, pupil = m.groups()
                        self.trials[current_trial].append(
                            {
                                "time": int(ts),
                                "x": float(x),
                                "y": float(y),
                                "pupil": float(pupil),
                            }
                        )


