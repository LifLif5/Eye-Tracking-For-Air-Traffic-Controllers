import pygame
import random
import sys
import time
import tkinter as tk
import math
import json
import os


import pylink

from ..Utils import generate_grid_positions, HEIGHT,WIDTH,WHITE, RED, GREEN, BLACK ,BLUE, DUMMY_MODE

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


def search_trial(trial_count, el_tracker, SEARCH_TYPE, N_DISTRACTORS, use_saved_config=False):
    el_tracker.sendMessage(f"TRIALID {trial_count}")
    el_tracker.sendMessage(f"TRIAL_START {trial_count}")
    screen.fill(WHITE)


    if use_saved_config:
        trial_data = load_trial_config(SEARCH_TYPE, trial_count)
        target_pos = tuple(trial_data["target_pos"])
        target_type = trial_data["target_type"]
        target_color = trial_data["target_color"]
        distractors = trial_data["distractors"]
    else:
        positions = generate_grid_positions(N_DISTRACTORS + 1, jitter=USE_NOISE)
        target_pos = random.choice(positions)
        distractors = []
        for pos in positions:
            if pos == target_pos:
                continue
            angle = random.choice([0, 90, 180, 270])
            if SEARCH_TYPE == "feature":
                distractors.append({"shape": "L_SHAPE", "color": "BLACK", "angle": angle, "pos": pos})
            elif SEARCH_TYPE == "pop_out":
                distractors.append({"shape": "L_SHAPE", "color": "BLACK", "angle": 0, "pos": pos})
            else:
                if random.random() < 0.5:
                    distractors.append({"shape": "L_SHAPE", "color": "BLUE", "angle": angle, "pos": pos})
                else:
                    distractors.append({"shape": "T_SHAPE", "color": "RED", "angle": angle, "pos": pos})

        if SEARCH_TYPE == "feature":
            target_type, target_color = "T_SHAPE", "BLACK"
        elif SEARCH_TYPE == "pop_out":
            target_type, target_color = "T_SHAPE", "RED"
        else:
            if random.random() < 0.5:
                target_type, target_color = "T_SHAPE", "BLUE"
            else:
                target_type, target_color = "L_SHAPE", "RED"

        trial_data = {
            "trial_id": trial_count,
            "target_pos": list(target_pos),
            "target_type": target_type,
            "target_color": target_color,
            "distractors": distractors
        }
        save_trial_config(SEARCH_TYPE, trial_data)

    focus_text = font.render("+", True, BLACK)
    
    focus_rect = focus_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(focus_text, focus_rect.topleft)
    el_tracker.sendMessage("FIX_POINT_DRAWN")
    pygame.display.flip()
    if not DUMMY_MODE:
        el_tracker.doDriftCorrect(WIDTH // 2,  HEIGHT // 2, 0, 0)
    time.sleep(1)
    # Draw stimuli
    screen.fill(WHITE)
    for d in distractors:
        shape = L_SHAPE if d["shape"] == "L_SHAPE" else T_SHAPE
        color = eval(d["color"])  # Caution: assumes color names are defined
        draw_letter(shape, color, d["pos"], d["angle"])

    target_shape = L_SHAPE if target_type == "L_SHAPE" else T_SHAPE
    draw_letter(target_shape, eval(target_color), target_pos)

    el_tracker.sendMessage("LETTERS_DRAWN")
    pygame.display.flip()

    # Event loop
    pygame.event.clear()
    start_time = time.time()
    while time.time() - start_time < 30:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                el_tracker.sendMessage("MOUSE_CLICKED")
                el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_OK)
                x, y = event.pos
                dist = ((x - target_pos[0]) ** 2 + (y - target_pos[1]) ** 2) ** 0.5
                if dist <= FONT_SIZE:
                    return time.time() - start_time
                else:
                    return 30 + time.time() - start_time
    return -1


def main_visual_search_experiment():
    el_tracker = pylink.getEYELINK()
    performance = []
    num_trials = 5
    # num_distractors = [7, 17, 31, 65, 119, 189]
    num_distractors = [7, 31, 119]
    
    trial_count = 0

    # --- Phase 1: Pop-out search ---
    pylink.flushGetkeyQueue()
    display_instructions([
        "Welcome to the Visual Search Task!",
        "Each trial you will see a + sign in the center of the screen.",
        "This is your fixation point.",
        "After a short delay, you will see a set of letters.",
        "Your task is to find the RED T letter and press it as quickly as possible.",
        "",
        "Press any key to start the experiment..."
    ])

    el_tracker.setOfflineMode()
    pylink.msecDelay(50)
    el_tracker.startRecording(1, 1, 1, 1)
    pylink.pumpDelay(100)
    el_tracker.sendMessage("PHASE1_POP_OUT_START")

    for distractors in num_distractors:
        for _ in range(num_trials):
            performance.append(search_trial(trial_count, el_tracker, "pop_out", distractors, use_saved_config=False))
            trial_count += 1

    el_tracker.sendMessage("PHASE1_POP_OUT_END")
    el_tracker.stopRecording()
    pylink.pumpDelay(100)

    # --- Phase 2: Feature search ---
    pylink.flushGetkeyQueue()
    display_instructions([
        "Great Job!",
        "Now we will do a more difficult task.",
        "All letters will be black.",
        "There will be many L letters and only one T letter.",
        "Your task is to find the T and press it as quickly as possible.",
        "",
        "Press any key to start the experiment..."
    ])

    el_tracker.setOfflineMode()
    pylink.msecDelay(50)
    el_tracker.startRecording(1, 1, 1, 1)
    pylink.pumpDelay(100)
    el_tracker.sendMessage("PHASE2_FEATURE_SEARCH_START")

    for distractors in num_distractors:
        for _ in range(num_trials):
            performance.append(search_trial(trial_count, el_tracker, "feature", distractors, use_saved_config=False))
            trial_count += 1

    el_tracker.sendMessage("PHASE2_FEATURE_SEARCH_END")
    el_tracker.stopRecording()
    pylink.pumpDelay(100)

    # --- Phase 3: Conjunction search ---
    pylink.flushGetkeyQueue()
    display_instructions([
        "Great Job!",
        "Now we move to an even harder task.",
        "You will see a set of letters, some of which are T and some are L.",
        "Your task is to find a BLUE T OR a RED L and press it as quickly as possible.",
        "",
        "Press any key to start the experiment..."
    ])

    el_tracker.setOfflineMode()
    pylink.msecDelay(50)
    el_tracker.startRecording(1, 1, 1, 1)
    pylink.pumpDelay(100)
    el_tracker.sendMessage("PHASE3_CONJUNCTION_SEARCH_START")

    for distractors in num_distractors:
        for _ in range(num_trials):
            performance.append(search_trial(trial_count, el_tracker, "conjunction", distractors, use_saved_config=False))
            trial_count += 1

    el_tracker.sendMessage("PHASE3_CONJUNCTION_SEARCH_END")
    el_tracker.stopRecording()
    pylink.pumpDelay(100)

    # --- End of experiment ---
    return performance
