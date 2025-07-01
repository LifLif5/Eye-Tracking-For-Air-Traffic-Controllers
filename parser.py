import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
from stimulus import Utils


class AscParser:
    """Parser for EDF2ASC *\*.asc* eye‑tracking logs supporting mono and binocular recordings.

    Besides the classic four‑column sample format (time, x, y, pupil), this parser
    detects and handles binocular lines that add a second triplet (x, y, pupil)
    for the other eye.  Columns are mapped to ``_l`` and ``_r`` suffixed fields
    when both eyes are present; otherwise the unsuffixed ``x``, ``y`` and
    ``pupil`` columns are retained for backward compatibility.
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

    # Support both mono (4 tokens) and binocular (7 tokens) samples.
    _RE_SAMPLE = re.compile(
        r"^(\d+)"                       # time stamp
        r"\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)"  # eye L or mono
        r"(?:\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*))?"  # opt. eye R
    )

    def __init__(self, filepath: str | Path):
        self.filepath: Path = Path(filepath)
        self.screen_width: Optional[int] = None
        self.screen_height: Optional[int] = None
        self.sample_rate: Optional[int] = None
        self.trials: Dict[str, List[Dict[str, float | int]]] = defaultdict(list)
        self.eye_mode: Optional[str] = None  # "mono" | "binocular"
        self._parse_file()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def get_screen_dims(self) -> Tuple[int | None, int | None]:
        return self.screen_width, self.screen_height

    def get_sample_rate(self) -> Optional[int]:
        return self.sample_rate

    def list_trials(self) -> List[str]:
        return list(self.trials.keys())

    def to_dataframe(self, trial_id: str) -> pd.DataFrame:
        if trial_id not in self.trials:
            raise KeyError(f"Trial '{trial_id}' not found.")

        df = pd.DataFrame(self.trials[trial_id])

        # ------------------------------------------------------------------
        # Coordinate normalisation
        # ------------------------------------------------------------------
        if self.screen_width and self.screen_height:
            # Identify all x/y columns dynamically so we also catch *_l / *_r
            for col in df.columns:
                if col.startswith("x"):
                    df[col] = df[col] / self.screen_width * Utils.WIDTH
                elif col.startswith("y"):
                    df[col] = df[col] / self.screen_height * Utils.HEIGHT

        # Add convenience average columns if binocular
        if {"x_l", "x_r"}.issubset(df.columns):
            df["x"] = df[["x_l", "x_r"]].mean(axis=1)
            df["y"] = df[["y_l", "y_r"]].mean(axis=1)
            df["pupil"] = df[["pupil_l", "pupil_r"]].mean(axis=1)

        return df.set_index("time")

    def summary(self) -> dict:
        return {
            "file": str(self.filepath),
            "screen_width": self.screen_width,
            "screen_height": self.screen_height,
            "sample_rate": self.sample_rate,
            "eye_mode": self.eye_mode,
            "n_trials": len(self.trials),
        }

    def get_messages(self, trial_id: str) -> List[Tuple[int, str]]:
        messages: List[Tuple[int, str]] = []
        with self.filepath.open("r", encoding="utf-8", errors="ignore") as fh:
            recording = False
            current_trial: Optional[str] = None
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

                # ----------------------------------------------------------
                # Meta messages
                # ----------------------------------------------------------
                if self.screen_width is None:
                    m = self._RE_DISPLAY.search(line)
                    if m:
                        self.screen_width = int(m.group(1))
                        self.screen_height = int(m.group(2))
                        continue

                if self.sample_rate is None:
                    m = self._RE_SR_MSG.match(line) or self._RE_SR_BLOCK.match(line)
                    if m:
                        self.sample_rate = int(round(float(m.group(1))))
                        continue

                # ----------------------------------------------------------
                # Trial boundaries
                # ----------------------------------------------------------
                m = self._RE_TRIAL_START.match(line)
                if m:
                    current_trial = m.group(1)
                    continue

                if self._RE_TRIAL_END.match(line):
                    current_trial = None
                    continue

                # ----------------------------------------------------------
                # Continuous sample stream
                # ----------------------------------------------------------
                if current_trial is not None:
                    m = self._RE_SAMPLE.match(line)
                    if m:
                        (
                            ts,
                            x_l,
                            y_l,
                            pupil_l,
                            x_r,
                            y_r,
                            pupil_r,
                        ) = m.groups()

                        sample = {
                            "time": int(ts),
                            "x_l": float(x_l),
                            "y_l": float(y_l),
                            "pupil_l": float(pupil_l),
                        }

                        if x_r is not None:
                            # Binocular: add second eye and flag mode
                            sample.update(
                                {
                                    "x_r": float(x_r),
                                    "y_r": float(y_r),
                                    "pupil_r": float(pupil_r),
                                }
                            )
                            self.eye_mode = "binocular"
                        else:
                            # Monocular: compact field names for backward compat
                            sample["x"] = sample.pop("x_l")
                            sample["y"] = sample.pop("y_l")
                            sample["pupil"] = sample.pop("pupil_l")
                            self.eye_mode = self.eye_mode or "mono"

                        self.trials[current_trial].append(sample)
