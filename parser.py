"""asc_parser_fixed.py – v1.1

Extended to handle *EyeLink* recordings that **lack explicit TRIALID
messages**.  If no trial boundaries are detected the parser will treat the
entire file as a single trial called ``_recording`` so the sample data is
still available.  In addition, the *TRIAL*‑start regex now recognises a set
of common aliases (e.g. ``TRIAL_START``) in a **case‑insensitive** fashion.

Other tweaks
============
* The `eye_mode` is now inferred on‑the‑fly the first time we encounter a
  sample line.  It no longer stays ``None`` in monocular logs.
* ``_RE_SAMPLE`` now accepts **tab** characters (`\t`) as delimiters in
  addition to spaces.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
from stimulus import Utils


class AscParser:
    """Parser for EDF2ASC ``*.asc`` logs supporting mono & binocular data."""

    # ------------------------------------------------------------------
    # Regular expressions
    # ------------------------------------------------------------------
    _RE_DISPLAY = re.compile(r"DISPLAY_COORDS\s+\d+\s+\d+\s+(\d+)\s+(\d+)")
    _RE_SR_MSG = re.compile(r"^MSG\s+\d+\s+SAMPLE_RATE\s+(\d+)")
    _RE_SR_BLOCK = re.compile(r"^(?:EVENTS|SAMPLES)\s+\S+\s+\S+\s+RATE\s+(\d+(?:\.\d+)?)", re.IGNORECASE)

    # Accept TRIALID, TRIAL_START, TRIALSTART … (case‑insensitive)
    _RE_TRIAL_START = re.compile(r"^MSG\s+\d+\s+(?:TRIALID|TRIAL[_ ]?START)\s+(\S+)", re.IGNORECASE)
    _RE_TRIAL_END = re.compile(r"^MSG\s+\d+\s+(?:END|STOP)", re.IGNORECASE)

    _RE_SBLINK = re.compile(r"^SBLINK\s+(\w)\s+(\d+)")
    _RE_EBLINK = re.compile(r"^EBLINK\s+(\w)\s+(\d+)\s+(\d+)")

    # Allow spaces **or tabs**
    _RE_SAMPLE = re.compile(
        r"^(\d+)"                                     # time stamp
        r"[ \t]+(-?\d+\.?\d*)[ \t]+(-?\d+\.?\d*)[ \t]+(-?\d+\.?\d*)"  # L / mono
        r"(?:[ \t]+(-?\d+\.?\d*)[ \t]+(-?\d+\.?\d*)[ \t]+(-?\d+\.?\d*))?"  # optional R
    )

    _FALLBACK_TRIAL_ID = "_recording"  # used when no TRIAL* messages exist

    # ------------------------------------------------------------------
    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)
        self.screen_width: Optional[int] = None
        self.screen_height: Optional[int] = None
        self.sample_rate: Optional[int] = None
        self.eye_mode: Optional[str] = None

        self.trials: Dict[str, List[Dict[str, float | int]]] = defaultdict(list)
        self.blinks: Dict[str, List[dict]] = defaultdict(list)
        self.blink_active: Dict[str, Dict[str, bool]] = defaultdict(lambda: {"L": False, "R": False})

        self._parse_file()

    # ------------------------------------------------------------------
    # Public API – unchanged
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

        # normalise coords
        if self.screen_width and self.screen_height:
            for col in df.columns:
                if col.startswith("x"):
                    df[col] = df[col] / self.screen_width * Utils.WIDTH
                elif col.startswith("y"):
                    df[col] = df[col] / self.screen_height * Utils.HEIGHT

        # binocular convenience cols
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
                    if msg.upper().startswith("TRIAL"):
                        current_trial = msg.split()[1]
                        recording = current_trial == str(trial_id)
                    elif msg.upper().startswith(("END", "STOP")):
                        recording = False
                    elif recording:
                        messages.append((ts, msg))
        return messages

    # ------------------------------------------------------------------
    # Core parser
    # ------------------------------------------------------------------
    def _parse_file(self) -> None:
        current_trial: Optional[str] = None

        with self.filepath.open("r", encoding="utf-8", errors="ignore") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue

                # meta – once
                if self.screen_width is None:
                    m = self._RE_DISPLAY.search(line)
                    if m:
                        self.screen_width, self.screen_height = map(int, m.groups())
                        continue

                if self.sample_rate is None:
                    m = self._RE_SR_MSG.match(line) or self._RE_SR_BLOCK.match(line)
                    if m:
                        self.sample_rate = int(round(float(m.group(1))))
                        continue

                # trial boundaries (if present)
                m = self._RE_TRIAL_START.match(line)
                if m:
                    current_trial = m.group(1)
                    continue

                if self._RE_TRIAL_END.match(line):
                    current_trial = None
                    continue

                # blink markers (only inside trials)
                if current_trial is not None:
                    m = self._RE_SBLINK.match(line)
                    if m:
                        eye, ts = m.groups()
                        self.blinks[current_trial].append({"eye": eye, "start": int(ts)})
                        self.blink_active[current_trial][eye] = True
                        continue

                    m = self._RE_EBLINK.match(line)
                    if m:
                        eye, _start, end_ = m.groups()
                        for blink in reversed(self.blinks[current_trial]):
                            if blink["eye"] == eye and "end" not in blink:
                                blink["end"] = int(end_)
                                break
                        self.blink_active[current_trial][eye] = False
                        continue

                # --------------------------------------------------
                # sample stream (numeric) – may appear outside trials
                # --------------------------------------------------
                m = self._RE_SAMPLE.match(line)
                if m:
                    if current_trial is None:
                        # No trial markers → fall back to single trial
                        current_trial = self._FALLBACK_TRIAL_ID
                    (
                        ts,
                        x_l,
                        y_l,
                        pupil_l,
                        x_r,
                        y_r,
                        pupil_r,
                    ) = m.groups()

                    # dot‑placeholders handled implicitly – they fail float()
                    try:
                        sample: Dict[str, float | int] = {
                            "time": int(ts),
                            "x_l": float(x_l),
                            "y_l": float(y_l),
                            "pupil_l": float(pupil_l),
                        }
                    except ValueError:
                        # skip malformed sample line (e.g. during blink)
                        continue

                    if x_r is not None:
                        sample.update({
                            "x_r": float(x_r),
                            "y_r": float(y_r),
                            "pupil_r": float(pupil_r),
                        })
                        self.eye_mode = "binocular"
                    else:
                        sample["x"] = sample.pop("x_l")
                        sample["y"] = sample.pop("y_l")
                        sample["pupil"] = sample.pop("pupil_l")
                        self.eye_mode = self.eye_mode or "mono"

                    # reset blink flags – valid sample reached
                    self.blink_active[current_trial]["L"] = False
                    self.blink_active[current_trial]["R"] = False

                    self.trials[current_trial].append(sample)
