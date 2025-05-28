import pygame
import random
import time
import math
import pylink
from ..Utils import  HEIGHT,WIDTH, WHITE, RED, GREEN, BLACK


BACKGROUND_COLOR = (230, 230, 230)
FIXATION_COLOR = (0, 0, 0)
FIXATION_SIZE = 20  # Size of the + sign

LETTER_COLOR = (50, 50, 180)
LETTER_FONT_SIZE = 48
TARGET_LETTERS = ['4', '5', '6']
DISTRACTOR_LETTER = '9'

FIXATION_TIME = 1.0
MAX_TRIAL_DURATION = 10.0
NUM_TRIALS = 1 #20 TODO
DIST_FROM_CENTER = 350  # Radius from center for letter placement

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Digit Identification Task")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, LETTER_FONT_SIZE)


def draw_fixation(cx, cy):
    focus_text = font.render("+", True, FIXATION_COLOR)
    focus_rect = focus_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(focus_text, focus_rect.topleft)


def draw_letter(letter, x, y):
    text_surf = font.render(letter, True, LETTER_COLOR)
    text_rect = text_surf.get_rect(center=(x, y))
    screen.blit(text_surf, text_rect)


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
    screen.fill(BACKGROUND_COLOR)
    y_offset = 100
    for line in lines:
        txt_surf = font.render(line, True, (0, 0, 0))
        screen.blit(txt_surf, (50, y_offset))
        y_offset += 50
    pygame.display.flip()
    wait_for_keypress()


def get_position_around_center(radius, angle_deg=None):
    angle = math.radians(angle_deg) if angle_deg is not None else random.uniform(0, 2 * math.pi)
    cx, cy = WIDTH // 2, HEIGHT // 2
    x = int(cx + radius * math.cos(angle))
    y = int(cy + radius * math.sin(angle))
    return x, y


def run_trial(el_tracker : pylink.EyeLink, trial_index ,with_distractors=False):
    screen.fill(BACKGROUND_COLOR)
    cx, cy = WIDTH // 2, HEIGHT // 2
    el_tracker.sendMessage(f"TRIALID {trial_index}")
    el_tracker.sendMessage(f"TRIAL_START {trial_index}")

    draw_fixation(cx, cy)
    el_tracker.sendMessage("FIX_POINT_DRAWN")
    pygame.display.flip()
    pygame.time.wait(int(FIXATION_TIME * 1000))

    target_letter = random.choice(TARGET_LETTERS)
    target_angle = random.uniform(0, 360)
    target_x, target_y = get_position_around_center(DIST_FROM_CENTER, target_angle)

    screen.fill(BACKGROUND_COLOR)
    draw_fixation(cx, cy)
    draw_letter(target_letter, target_x, target_y)

    if with_distractors:
        distractor_angles = [(target_angle + offset) % 360 for offset in [90, 180, 270]]
        for angle in distractor_angles:
            x, y = get_position_around_center(DIST_FROM_CENTER, angle)
            draw_letter(DISTRACTOR_LETTER, x, y)

    pygame.display.flip()

    pygame.event.clear()
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        if elapsed > MAX_TRIAL_DURATION:
            return -1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
                response = event.unicode.upper()
                return elapsed if response == target_letter else -1


def main_abrupt_onset_experiment(el_tracker):
    display_instructions([
        "Digit Identification Task",
        "A single digit (4, 5, or 6) will appear around the center.",
        "Press the matching key as quickly and accurately as possible.",
        "Press any key to start Phase 1 (no distractors)..."
    ])
    el_tracker.setOfflineMode()
    el_tracker.startRecording(1, 1, 1, 1)
    pylink.pumpDelay(100)  # allow tracker to stabilize
    reaction_times_phase1 = []
    for _ in range(NUM_TRIALS):
        rt = run_trial(el_tracker ,0,with_distractors=False)
        reaction_times_phase1.append(rt)
    pylink.pumpDelay(100)
    el_tracker.stopRecording()
    display_instructions([
        "Phase 2: Distractor Digits",
        "Now you'll see extra digits (9s) appearing along with the target.",
        "Focus on the correct digit (4, 5, or 6) and ignore the rest.",
        "Press any key to begin..."
    ])

    reaction_times_phase2 = []
    for _ in range(NUM_TRIALS):
        rt = run_trial(el_tracker ,0,with_distractors=True)
        reaction_times_phase2.append(rt)

    display_instructions([
        "Experiment complete.",
        "Press any key to exit."
    ])
    pylink.pumpDelay(100)
    el_tracker.stopRecording()
    print("Phase 1 Reaction Times:", reaction_times_phase1)
    print("Phase 2 Reaction Times (with distractors):", reaction_times_phase2)

