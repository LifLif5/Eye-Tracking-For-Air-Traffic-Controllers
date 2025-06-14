import pygame
import random
import sys
import time
import tkinter as tk
import math
import json
import os

from parser import AscParser


from ..Utils import  HEIGHT,WIDTH,WHITE, RED, GREEN, BLACK ,BLUE

# Initialize pygame
pygame.init()

# Parameters
FONT_SIZE = 40
USE_NOISE = True  # Set to False for exact center, True for jittered

# Shapes
T_SHAPE = "T"
L_SHAPE = "L"
FILE_LOCATION = "stimulus/VisualSearch/"
# Initialize screen
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Visual Search Task")
font = pygame.font.SysFont(None, FONT_SIZE, bold=True)
instructions_font = pygame.font.SysFont(None, FONT_SIZE, bold=False)

def save_trial_config(search_type, trial_data):
    filename = f"{FILE_LOCATION}{search_type.lower()}_trials.json"
    all_trials = []
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            all_trials = json.load(f)
    all_trials.append(trial_data)
    with open(filename, 'w') as f:
        json.dump(all_trials, f, indent=2)

def load_trial_config(search_type, trial_count):
    filename = f"{FILE_LOCATION}{search_type.lower()}_trials.json"
    with open(filename, 'r') as f:
        all_trials = json.load(f)
    for trial in all_trials:
        if trial["trial_id"] == trial_count:
            return trial
    raise ValueError(f"Trial with trial_id={trial_count} not found in {filename}")


def draw_letter(letter, color, pos, angle=0):
    text_surface = font.render(letter, True, color)
    text_surface = pygame.transform.rotate(text_surface, angle)
    rect = text_surface.get_rect(center=(pos[0], pos[1]))
    screen.blit(text_surface, rect.topleft)


def wait_for_keypress():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
                return
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()


def display_instructions(lines):
    screen.fill(WHITE)
    y_offset = 100
    for line in lines:
        txt_surf = instructions_font.render(line, True, (0, 0, 0))
        screen.blit(txt_surf, (50, y_offset))
        y_offset += 50
    pygame.display.flip()
    wait_for_keypress()


def quit_check(events):
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            raise SystemExit("Experiment terminated by user.")
        
def search_trial(trial_index: int, gaze_data, messages, SEARCH_TYPE: str):
    trial_data = load_trial_config(SEARCH_TYPE, trial_index)
    target_pos = tuple(trial_data["target_pos"])
    target_type = trial_data["target_type"]
    target_color = trial_data["target_color"]
    distractors = trial_data["distractors"]

    target_shape = L_SHAPE if target_type == "L_SHAPE" else T_SHAPE

    # ---- Init gaze/message pointers ----
    gaze_ptr = 0
    msg_ptr = 0
    show_message = None
    message_timer = 0
    clock = pygame.time.Clock()

    # ---- Phase 1: fixation cross with gaze ----
    start_time = pygame.time.get_ticks()
    focus_duration = 1000  # ms
    while pygame.time.get_ticks() - start_time < focus_duration:
        elapsed = pygame.time.get_ticks() - start_time
        events = pygame.event.get()
        quit_check(events)

        screen.fill(WHITE)
        focus_text = font.render("+", True, BLACK)
        focus_rect = focus_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(focus_text, focus_rect.topleft)

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

        if show_message and pygame.time.get_ticks() - message_timer < 1000:
            text = font.render(show_message, True, GREEN)
            screen.blit(text, (20, 20))

        pygame.display.flip()
        clock.tick(30)

    # ---- Phase 2: stimuli + gaze/messages ----
    start_time = pygame.time.get_ticks()
    done = False
    while not done:
        elapsed = pygame.time.get_ticks() - start_time
        events = pygame.event.get()
        for event in events:
            quit_check([event])
            if event.type == pygame.MOUSEBUTTONDOWN:
                done = True

        screen.fill(WHITE)

        # Draw distractors
        for d in distractors:
            shape = L_SHAPE if d["shape"] == "L_SHAPE" else T_SHAPE
            color = eval(d["color"])
            draw_letter(shape, color, d["pos"], d["angle"])

        draw_letter(target_shape, eval(target_color), target_pos)

        # Gaze
        while gaze_ptr < gaze_data.shape[0] and gaze_data[gaze_ptr, 0] <= elapsed + focus_duration:
            gaze_ptr += 1
        if gaze_ptr < gaze_data.shape[0]:
            gx, gy = gaze_data[gaze_ptr - 1, 1:].astype(int)
            pygame.draw.circle(screen, GREEN, (gx, gy), 8, 2)
        else:
            done = True

        # Messages
        while msg_ptr < len(messages) and messages[msg_ptr][0] <= elapsed + focus_duration:
            show_message = messages[msg_ptr][1]
            message_timer = pygame.time.get_ticks()
            print(f"[MSG @ {elapsed + focus_duration} ms]: {show_message}")
            msg_ptr += 1

        if show_message and pygame.time.get_ticks() - message_timer < 1000:
            text = font.render(show_message, True, GREEN)
            screen.blit(text, (20, 20))

        pygame.display.flip()
        clock.tick(30)

def visual_search_visualization(ascDataParsed : AscParser):
    num_trials = 1
    num_distractors = [7, 17, 31, 65, 119, 189]
    trial_count = 0
    
    for distractors in num_distractors:
        for _ in range(num_trials):
            df = ascDataParsed.to_dataframe(str(trial_count))
            df["rel_ms"] = df.index - df.index[0]
            gaze = df[["rel_ms", "x", "y"]].to_numpy()
            messages = ascDataParsed.get_messages(trial_count)
            messages = [(t - df.index[0], msg) for t, msg in messages]
            search_trial(trial_count,gaze,messages,"pop_out")
            trial_count += 1



    for distractors in num_distractors:
        for _ in range(num_trials):
            df = ascDataParsed.to_dataframe(str(trial_count))
            df["rel_ms"] = df.index - df.index[0]
            gaze = df[["rel_ms", "x", "y"]].to_numpy()
            messages = ascDataParsed.get_messages(trial_count)
            messages = [(t - df.index[0], msg) for t, msg in messages]
            search_trial(trial_count,gaze,messages,"feature")
            trial_count += 1

    for distractors in num_distractors:
        for _ in range(num_trials):
            df = ascDataParsed.to_dataframe(str(trial_count))
            df["rel_ms"] = df.index - df.index[0]
            gaze = df[["rel_ms", "x", "y"]].to_numpy()
            messages = ascDataParsed.get_messages(trial_count)
            messages = [(t - df.index[0], msg) for t, msg in messages]
            search_trial(trial_count,gaze,messages,"conjunction")
            trial_count += 1


