import pygame
import random  # not used but kept in case future extensions need it
import numpy as np
import tkinter as tk  # not used but kept for potential GUI prompts
import yaml
import os
import pylink
from MouseMovements.MouseTracker import MouseRecorder  # noqa: F401 (side‑effects)
from parser import AscParser  # local AscParser (now binocular‑aware)
from .Mot import BALL_RADIUS
from ..Utils import (
    generate_grid_positions,  # noqa: F401
    HEIGHT,
    WIDTH,
    WHITE,
    RED,
    GREEN,
    BLACK,
    DISPLAY_SIZE_MULTIPLIER
)

# Extra colours for new overlays
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# ---------------------------------------------------------------------
# Pygame initialisation
# ---------------------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Multi‑Object Tracking (MOT)")
font = pygame.font.SysFont(None, 40)

# ---------------------------------------------------------------------
# Load / initialise YAML config for stimulus playback
# ---------------------------------------------------------------------
CONFIG_PATH = "stimulus\\MOT\\mot_config.yaml"
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
else:
    raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH!r}.")


# ---------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------

def quit_check(events):
    """Abort the experiment if <Esc> is pressed."""
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            raise SystemExit("Experiment terminated by user.")


# ---------------------------------------------------------------------
# Trial‑level playback
# ---------------------------------------------------------------------

def mot_trial(
    trial_index: int,
    gaze_left: np.ndarray,
    gaze_right: np.ndarray | None,
    messages: list[tuple[int, str]],
):
    """Replays one MOT trial with binocular eye and mouse overlays.

    Parameters
    ----------
    trial_index : int
        Index into ``config['trials']``.
    gaze_left : (N, 3) ndarray
        Columns ``rel_ms, x, y`` for the *left* eye (or mono eye).
    gaze_right : (N, 3) ndarray | None
        Same for the *right* eye; *None* for monocular recordings.
    messages : list[(time_ms, msg_str)]
        Relative‑time message tuples, already aligned to trial start.
    """

    # --------------------------------------------------------------
    # Parse trial parameters from YAML
    # --------------------------------------------------------------
    trial_cfg = config["trials"][trial_index]
    num_objects, num_targets, trial_duration, speed = trial_cfg["params"]
    radius = BALL_RADIUS
    speed = int(speed * DISPLAY_SIZE_MULTIPLIER)  # Scale speed for display size

    # --------------------------------------------------------------
    # Initial object positions / directions
    # --------------------------------------------------------------
    dirs = []
    for d in trial_cfg["directions"]:
        v = np.asarray(d, dtype=float)
        v = v / np.linalg.norm(v) * speed
        dirs.append(v.tolist())

    objects = [
        {"pos": list(pos), "dir": dir.copy()} for pos, dir in zip(trial_cfg["locations"], dirs)
    ]
    target_indices = trial_cfg["targets"]

    # --------------------------------------------------------------
    # Separate mouse‑position messages from general EyeLink ones
    # --------------------------------------------------------------
    mouse_log: list[tuple[int, int, int]] = []  # (rel_ms, x, y)
    other_msgs: list[tuple[int, str]] = []
    for ts, msg in messages:
        if msg.startswith("!MOUSE_POS"):
            try:
                _, x_s, y_s = msg.split()
                mouse_log.append((ts, int(float(x_s)), int(float(y_s))))
            except ValueError:
                # Malformed message – ignore silently
                continue
        else:
            other_msgs.append((ts, msg))

    # Runtime pointers into the various time‑series
    gaze_l_ptr = 0
    gaze_r_ptr = 0
    mouse_ptr = 0
    msg_ptr = 0

    show_message: str | None = None
    message_timer = 0

    # --------------------------------------------------------------
    # Main replay helper (phased)
    # --------------------------------------------------------------
    def replay_loop(duration_ms: int, draw_objects: bool = True):
        nonlocal gaze_l_ptr, gaze_r_ptr, mouse_ptr, msg_ptr, show_message, message_timer
        clock = pygame.time.Clock()
        loop_start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - loop_start < duration_ms:
            elapsed = pygame.time.get_ticks() - global_start

            # --------------------------------------------------
            # House‑keeping events
            # --------------------------------------------------
            events = pygame.event.get()
            quit_check(events)
            screen.fill(BLACK)

            # --------------------------------------------------
            # MOT dots
            # --------------------------------------------------
            if draw_objects:
                for obj in objects:
                    obj["pos"][0] += int(obj["dir"][0])
                    obj["pos"][1] += int(obj["dir"][1])

                    # Bounce off walls
                    if obj["pos"][0] <= radius or obj["pos"][0] >= WIDTH - radius:
                        obj["dir"][0] *= -1
                    if obj["pos"][1] <= radius or obj["pos"][1] >= HEIGHT - radius:
                        obj["dir"][1] *= -1
                    pygame.draw.circle(screen, WHITE, obj["pos"], radius)
            else:
                for idx, obj in enumerate(objects):
                    col = RED if idx in target_indices else WHITE
                    pygame.draw.circle(screen, col, obj["pos"], radius)

            # --------------------------------------------------
            # Gaze – left eye (always present)
            # --------------------------------------------------
            while gaze_l_ptr < gaze_left.shape[0] and gaze_left[gaze_l_ptr, 0] <= elapsed:
                gaze_l_ptr += 1
            if gaze_l_ptr:
                gx, gy = gaze_left[gaze_l_ptr - 1, 1:].astype(int)
                pygame.draw.circle(screen, GREEN, (gx, gy), 8, 2)

            # --------------------------------------------------
            # Gaze – right eye (optional)
            # --------------------------------------------------
            if gaze_right is not None:
                while gaze_r_ptr < gaze_right.shape[0] and gaze_right[gaze_r_ptr, 0] <= elapsed:
                    gaze_r_ptr += 1
                if gaze_r_ptr:
                    gx_r, gy_r = gaze_right[gaze_r_ptr - 1, 1:].astype(int)
                    pygame.draw.circle(screen, BLUE, (gx_r, gy_r), 8, 2)

            # --------------------------------------------------
            # Mouse overlay (optional)
            # --------------------------------------------------
            while mouse_ptr < len(mouse_log) and mouse_log[mouse_ptr][0] <= elapsed:
                mouse_ptr += 1
            if mouse_ptr:
                mx, my = mouse_log[mouse_ptr - 1][1:]
                # Draw a crosshair for visibility
                pygame.draw.line(screen, YELLOW, (mx - 10, my), (mx + 10, my), 2)
                pygame.draw.line(screen, YELLOW, (mx, my - 10), (mx, my + 10), 2)

            # --------------------------------------------------
            # Non‑mouse EyeLink messages
            # --------------------------------------------------
            while msg_ptr < len(other_msgs) and other_msgs[msg_ptr][0] <= elapsed:
                show_message = other_msgs[msg_ptr][1]
                message_timer = pygame.time.get_ticks()
                msg_ptr += 1
                if show_message == f"TRIAL_RESULT {pylink.TRIAL_OK}":
                    return  # end phase early on trial completion

            if show_message and pygame.time.get_ticks() - message_timer < 1000:
                text_surf = font.render(show_message, True, GREEN)
                screen.blit(text_surf, (20, 20))

            # --------------------------------------------------
            # Refresh at ~30 Hz (eye‑data already discrete)
            # --------------------------------------------------
            pygame.display.flip()
            clock.tick(30)

    # --------------------------------------------------------------
    # Trial timeline: cue → motion → selection prompt
    # --------------------------------------------------------------
    global_start = pygame.time.get_ticks()

    # 1) Cue phase – highlight targets, gaze visible
    replay_loop(2000, draw_objects=False)

    # 2) Motion phase
    replay_loop(trial_duration * 1000, draw_objects=True)

    # 3) Prompt participant to click targets (static scene)
    prompt_surf = font.render("Click on the targets!", True, GREEN)
    screen.blit(prompt_surf, prompt_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    pygame.display.flip()

    replay_loop(10_000, draw_objects=False)


# ---------------------------------------------------------------------
# High‑level visualisation entry point
# ---------------------------------------------------------------------

def visualize_mot_experiment(asc_data_parsed: AscParser, n_trials: int | None = None):
    """Play back the first ``n_trials`` of the experiment (default: all)."""
    try:
        trial_ids = asc_data_parsed.list_trials()
        n_trials = n_trials or len(trial_ids)
        print(f"Visualising {n_trials} trials out of {len(trial_ids)} total trials.")
        for i in range(n_trials):
            trial_id = str(trial_ids[i])
            df = asc_data_parsed.to_dataframe(trial_id)  # already normalised

            # Time alignment to trial start (0 ms at first sample)
            df["rel_ms"] = df.index - df.index[0]

            if {"x_l", "y_l"}.issubset(df.columns):
                # Binocular recording
                gaze_l = df[["rel_ms", "x_l", "y_l"]].to_numpy()
                gaze_r = df[["rel_ms", "x_r", "y_r"]].to_numpy()
            else:
                # Monocular recording – duplicate array for API consistency
                gaze_l = df[["rel_ms", "x", "y"]].to_numpy()
                gaze_r = None

            msg_raw = asc_data_parsed.get_messages(trial_id)
            if not msg_raw:
                continue  # skip if trial has no messages (unlikely)

            start_ts = msg_raw[0][0]  # first MSG is TRIALID by construction
            rel_msgs = [(ts - start_ts, msg) for ts, msg in msg_raw[1:]]

            mot_trial(i-1, gaze_l, gaze_r, rel_msgs)

    except SystemExit:
        pass  # graceful termination
