import pygame
import random
import sys
import time
import tkinter as tk
import math
import json
import os
import glob

import pylink

from ..Utils import generate_grid_positions, HEIGHT,WIDTH,WHITE, RED, GREEN, BLACK ,BLUE, DUMMY_MODE,MOUSE_POS_MSG

# Initialize pygame
pygame.init()

# Parameters
FONT_SIZE = 40
USE_NOISE = True  # Set to False for exact center, True for jittered

# Shapes
T_SHAPE = "T"
L_SHAPE = "L"
FILE_LOCATION = "stimulus/VisualSearch/"
WALDO_FOLDER = "stimulus/VisualSearch/waldo_images/"
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


def display_instructions(lines, waldo_image=False):
    screen.fill(WHITE)
    y_offset = 100
    for line in lines:
        txt_surf = instructions_font.render(line, True, (0, 0, 0))
        screen.blit(txt_surf, (50, y_offset))
        y_offset += 50

    if waldo_image:
        # Load and display example Waldo image
        example_path = os.path.join(WALDO_FOLDER, "waldo_example.png")
        if os.path.exists(example_path):
            waldo_img = pygame.image.load(example_path).convert_alpha()
            # Scale to width = 200 px
            w_ratio = 200 / waldo_img.get_width()
            new_size = (200, int(waldo_img.get_height() * w_ratio))
            waldo_img = pygame.transform.scale(waldo_img, new_size)

            # Blit to bottom center
            screen.blit(waldo_img, (WIDTH//2 - new_size[0]//2, HEIGHT - new_size[1] - 50))
        else:
            print("Example Waldo image not found at", example_path)

    pygame.display.flip()
    wait_for_keypress()

def search_trial(trial_count, el_tracker, SEARCH_TYPE, N_DISTRACTORS, use_saved_config=False):
    el_tracker.sendMessage(f"TRIALID {trial_count}")
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
    el_tracker.sendMessage(f"TRIAL_START {trial_count}")

    while time.time() - start_time < 30:
        x, y = pygame.mouse.get_pos()
        el_tracker.sendMessage(f"{MOUSE_POS_MSG} {x} {y}")

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left mouse button
                el_tracker.sendMessage(f"!LEFT_MOUSE_DOWN {x} {y}") 
                el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_OK)
                x, y = event.pos
                dist = ((x - target_pos[0]) ** 2 + (y - target_pos[1]) ** 2) ** 0.5
                if dist <= FONT_SIZE:
                    return time.time() - start_time
                else:
                    # keep going; wrong click
                    pass
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:  # Left mouse button up
                el_tracker.sendMessage(f"!LEFT_MOUSE_UP {x} {y}")

    return -1


def waldo_trial(trial_id, el_tracker, image_surf, bbox, timeout=20):
    """Display one Where's Waldo scene and return RT (-1 if timeout)."""
    el_tracker.sendMessage(f"TRIALID {trial_id}")

    screen.fill(WHITE)
    focus_text = font.render("+", True, BLACK)
    focus_rect = focus_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(focus_text, focus_rect.topleft)
    el_tracker.sendMessage("FIX_POINT_DRAWN")
    pygame.display.flip()
    if not DUMMY_MODE:
        el_tracker.doDriftCorrect(WIDTH // 2,  HEIGHT // 2, 0, 0)

    screen.fill(WHITE)
    screen.blit(image_surf, (0, 0))
    pygame.display.flip()

    start = time.time()
    pygame.event.clear()

    el_tracker.sendMessage(f"TRIAL_START {trial_id}")

    while time.time() - start < timeout:
        x, y = pygame.mouse.get_pos()
        el_tracker.sendMessage(f"{MOUSE_POS_MSG} {x} {y}")

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                x, y = event.pos
                el_tracker.sendMessage(f"!LEFT_MOUSE_DOWN {x} {y}")
                if bbox.collidepoint(x, y):
                    el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_OK)
                    return time.time() - start    # hit
                else:
                    # keep going; wrong click
                    pass
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:  # Left mouse button up
                el_tracker.sendMessage(f"!LEFT_MOUSE_UP {x} {y}")
    el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_TIMEOUT)
    return -1

def main_visual_search_experiment():
    el_tracker = pylink.getEYELINK()
    performance = []
    num_trials = 8
    # num_distractors = [7, 17, 31, 65, 119, 189]
    num_distractors = [7, 31, 65]
    
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


    # ----------------------------------------------------------
    # --- Phase 4: Waldo scenes ---  
    #
    # preload images & bboxes
    with open(WALDO_FOLDER + "waldo_boxes.json", "r") as f:
        waldo_boxes = json.load(f)
    waldo_imgs = sorted(glob.glob(WALDO_FOLDER + "*.jpg"))[:10]   # 10 scenes

    # instructions
    display_instructions([
        "Last part!",
        "You will see crowded cartoon scenes.",
        "Find WALDO (example below) and click him.",
        "If you cannot find him within 20 s the scene will advance.",
        "",
        "Press any key to continue..."
    ], waldo_image=True)

    el_tracker.setOfflineMode()
    pylink.msecDelay(50)
    el_tracker.startRecording(1, 1, 1, 1)
    el_tracker.sendMessage("PHASE4_WALDO_START")

    for img_path in waldo_imgs:
        surf = pygame.image.load(img_path).convert()
        # scale to full screen
        surf = pygame.transform.scale(surf, (WIDTH, HEIGHT))
        # bbox from JSON; adjust if the image was scaled
        bx, by, bw, bh = waldo_boxes[os.path.basename(img_path)]
        scale_x = WIDTH  / surf.get_width()
        scale_y = HEIGHT / surf.get_height()
        bbox = pygame.Rect(bx*scale_x, by*scale_y, bw*scale_x, bh*scale_y)

        rt = waldo_trial(trial_count, el_tracker, surf, bbox, timeout=12)
        performance.append(rt)
        trial_count += 1

    el_tracker.sendMessage("PHASE4_WALDO_END")
    el_tracker.stopRecording()
    pylink.pumpDelay(100)
    # ----------------------------------------------------------


    # --- End of experiment ---
    return performance
