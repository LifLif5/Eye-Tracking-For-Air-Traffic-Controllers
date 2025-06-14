import pygame
import random
import numpy as np
import tkinter as tk
import yaml
import os
import pylink
from MouseMovements.MouseTracker import MouseRecorder
from parser import AscParser
from ..Utils import generate_grid_positions, HEIGHT,WIDTH,WHITE, RED, GREEN, BLACK


# Init pygame
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Multi-Object Tracking (MOT)")
font = pygame.font.SysFont(None, 40)


# Load or initialize config
CONFIG_PATH = "stimulus\\MOT\\mot_config.yaml"
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

def quit_check(events):
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            raise SystemExit("Experiment terminated by user.")


def mot_trial(trial_index, gaze_data, messages):

    trial = config["trials"][trial_index]
    num_objects, num_targets = trial["params"]
    radius, speed = 20, 5

    # Normalize directions
    dirs = []
    for d in trial["directions"]:
        v = np.array(d)
        v = v / np.linalg.norm(v) * speed
        dirs.append(v.tolist())

    objects = [{"pos": list(pos), "dir": dir[:]} for pos, dir in zip(trial["locations"], dirs)]
    target_indices = trial["targets"]



       # --- Common replay logic ---
    def replay_loop(duration_ms: int, draw_objects: bool = True):
        nonlocal gaze_ptr, msg_ptr, show_message, message_timer
        clock = pygame.time.Clock()
        loop_start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - loop_start < duration_ms:
            elapsed = pygame.time.get_ticks() - start_time
            events = pygame.event.get()
            quit_check(events)
            screen.fill(BLACK)

            if draw_objects:
                for obj in objects:
                    obj["pos"][0] += int(obj["dir"][0])
                    obj["pos"][1] += int(obj["dir"][1])
                    if obj["pos"][0] <= radius or obj["pos"][0] >= WIDTH - radius:
                        obj["dir"][0] *= -1
                    if obj["pos"][1] <= radius or obj["pos"][1] >= HEIGHT - radius:
                        obj["dir"][1] *= -1
                    pygame.draw.circle(screen, WHITE, obj["pos"], radius)
            else:
                for i, obj in enumerate(objects):
                    color = RED if i in target_indices else WHITE
                    pygame.draw.circle(screen, color, obj["pos"], radius)

            # Gaze
            while gaze_ptr < gaze_data.shape[0] and gaze_data[gaze_ptr, 0] <= elapsed:
                gaze_ptr += 1
            if gaze_ptr:
                gx, gy = gaze_data[gaze_ptr - 1, 1:].astype(int)
                pygame.draw.circle(screen, GREEN, (gx, gy), 8, 2)

            # Messages
            while msg_ptr < len(messages) and messages[msg_ptr][0] <= elapsed:
                show_message = messages[msg_ptr][1]
                message_timer = pygame.time.get_ticks()
                print(f"[MSG @ {elapsed} ms]: {show_message}")
                msg_ptr += 1
                if show_message == "TRIAL_RESULT %d" % pylink.TRIAL_OK:
                    return

            if show_message and pygame.time.get_ticks() - message_timer < 1000:
                text = font.render(show_message, True, GREEN)
                screen.blit(text, (20, 20))

            pygame.display.flip()
            clock.tick(30)

    # --- Full trial timeline ---
    start_time = pygame.time.get_ticks()
    gaze_ptr = 0
    msg_ptr = 0
    show_message = None
    message_timer = 0

    # Phase 1: Show targets (static objects, gaze visible)
    replay_loop(2000, draw_objects=False)

    # Phase 2: Movement + gaze
    replay_loop(10000, draw_objects=True)

    # Phase 3: Prompt
    text = font.render('Click on the targets!', True, GREEN)
    screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    pygame.display.flip()

    replay_loop(10000, draw_objects=False)

    


def visualize_mot_experiment(ascDataParsed : AscParser):
    try:
        
 
        # for i in range(len(config["trials"])):
        for i in range(5):

            df = ascDataParsed.to_dataframe(str(i))   # already in Utils.WIDTH/HEIGHT units
            df["rel_ms"] = df.index - df.index[0]             # time since TRIALID, in ms
            gaze = df[["rel_ms", "x", "y"]].to_numpy()        # fast NumPy array


            msg_raw = ascDataParsed.get_messages(i)
            start_time = msg_raw[0][0]  # TRIALID timestamp
            messages = [(ts - start_time, msg) for ts, msg in msg_raw[1:]]

            mot_trial(i, gaze,messages)

    except SystemExit:
        pass