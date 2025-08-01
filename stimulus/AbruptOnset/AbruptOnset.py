import pygame
import random
import time
import math
import pylink
import json
from ..Utils import drift_correction,display_instructions, HEIGHT,WIDTH, WHITE, RED, GREEN, BLACK, DUMMY_MODE, DISPLAY_SIZE_MULTIPLIER

opening_instructions = [
    "ברוכים הבאים למשימת זיהוי הספרות!",
    "משימה זו מורכבת משני חלקים.",
    "לחצו על מקש כלשהו כדי להמשיך לחלק הראשון..."
]

phase1_instructions = [
    "חלק ראשון: זיהוי ספרה בודדת.",
    "בכל סיבוב, יופיע + במרכז המסך, עליכם להסתכל על המרכז שלו.",
    "לאחר מכן תופיע ספרה אחת (4, 5 או 6) במרחק קבוע מהמרכז,",
    "המטרה שלכם היא ללחוץ (במקלדת) על מקש הספרה המתאימה במהירות ובדיוק",
    "(לאחר שהספרה מופיעה אתם כבר לא צריכים להסתכל על ה +)",
    "",
    "",
    "יהיו 50 סיבובים כאלו,",
    "לחצו על מקש כלשהו כדי להתחיל..."
]

phase2_instructions = [
    "חלק שני: ספרות מסיחות.",
    "כעת תופיע ספרת מטרה (4, 5 או 6) יחד עם 3 ספרות מסיחות (7).",
    "המטרה שלכם היא לזהות את ספרת המטרה בלבד וללחוץ על מקש מתאים במהירות ובדיוק.",
    "המסיחים אינם רלוונטיים — התעלמו מהם.",
    "",
    "",
    "גם הפעם יהיו 50 סיבובים,",
    "לחצו על מקש כלשהו כדי להתחיל..."
]

ending_instructions = [
    "סיימתם את המשימה!!!!!",
    "לחצו על מקש כלשהו כדי להמשיך."
]


BACKGROUND_COLOR = (230, 230, 230)
FIXATION_COLOR = (0, 0, 0)
FIXATION_SIZE = int(40  * DISPLAY_SIZE_MULTIPLIER) # Size of the + sign

LETTER_COLOR = (50, 50, 180)
LETTER_FONT_SIZE = int(30  * DISPLAY_SIZE_MULTIPLIER)
TARGET_LETTERS = ['4', '5', '6']
VALID_KEYS = [pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7,
               pygame.K_KP4, pygame.K_KP5, pygame.K_KP6, pygame.K_KP7]
DISTRACTOR_LETTER = '7'

FIXATION_TIME = 1.0
MAX_TRIAL_DURATION = 10.0
NUM_TRIALS = 50 #TODO 50
DIST_FROM_CENTER = 500  * DISPLAY_SIZE_MULTIPLIER # Radius from center for letter placement

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Digit Identification Task")
clock = pygame.time.Clock()
fixation_font = pygame.font.SysFont(None, FIXATION_SIZE)
letter_font = pygame.font.SysFont(None, LETTER_FONT_SIZE)

def build_config_file():
    rng = random.Random()  # Independent random generator instance

    pairs = []
    for _ in range(100):
        target_letter = rng.choice(TARGET_LETTERS)
        target_angle = rng.uniform(0, 360)
        pairs.append({"letter": target_letter, "angle": round(target_angle, 4)})

    # Save to config file
    with open("stimulus/AbruptOnset/config_pairs.json", "w") as f:
        json.dump(pairs, f, indent=2)

def load_pair_by_index(index, filename="stimulus/AbruptOnset/config_pairs.json"):
    with open(filename, "r") as f:
        data = json.load(f)
    if index < 0 or index >= len(data):
        raise IndexError(f"Index {index} out of range. File contains {len(data)} pairs.")
    
    pair = data[index]
    return pair["letter"], float(pair["angle"])

def draw_fixation(cx, cy):
    focus_text = fixation_font.render("+", True, FIXATION_COLOR)
    focus_rect = focus_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(focus_text, focus_rect.topleft)


def draw_letter(letter, x, y):
    text_surf = letter_font.render(letter, True, LETTER_COLOR)
    text_rect = text_surf.get_rect(center=(x, y))
    screen.blit(text_surf, text_rect)




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

    target_letter, target_angle = load_pair_by_index(trial_index)
    # target_letter = random.choice(TARGET_LETTERS)
    # target_angle = random.uniform(0, 360)
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
    el_tracker.sendMessage("TARGET_DRAWN")
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
                if event.key in VALID_KEYS:
                    pressed_letter = None
                    if event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_4, pygame.K_KP4):
                            pressed_letter = '4'
                        elif event.key in (pygame.K_5, pygame.K_KP5):
                            pressed_letter = '5'
                        elif event.key in (pygame.K_6, pygame.K_KP6):
                            pressed_letter = '6'
                        elif event.key in (pygame.K_7, pygame.K_KP7):
                            pressed_letter = '7'
                        

                    el_tracker.sendMessage("KEY_PRESSED")
                    el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_OK)
                    return elapsed if pressed_letter == target_letter else -1


def main_abrupt_onset_experiment():
    display_instructions(opening_instructions,screen)
    el_tracker = pylink.getEYELINK()

    # Flush keypress queue to avoid skipping screens
    pylink.flushGetkeyQueue()

    pygame.mouse.set_visible(False)
    # Instructions before Phase 1
    display_instructions(phase1_instructions, screen)

    # Start Phase 1 Recording

    el_tracker.sendMessage("PHASE1_START")

    reaction_times = []
    trial_count = 0
    for _ in range(NUM_TRIALS):
        if trial_count %10 ==0:
            drift_correction(el_tracker)
        rt = run_trial(el_tracker, trial_count, with_distractors=False)
        reaction_times.append(rt)
        trial_count += 1

    el_tracker.sendMessage("PHASE1_END")
    el_tracker.stopRecording()
    pylink.pumpDelay(100)

    # Instructions before Phase 2
    pylink.flushGetkeyQueue()
    display_instructions(phase2_instructions, screen)

    # Start Phase 2 Recording
    el_tracker.sendMessage("PHASE2_START")

    for _ in range(NUM_TRIALS):
        if trial_count %10 ==0:
            drift_correction(el_tracker)
        rt = run_trial(el_tracker, trial_count, with_distractors=True)
        reaction_times.append(rt)
        trial_count += 1

    el_tracker.sendMessage("PHASE2_END")
    el_tracker.stopRecording()
    pylink.pumpDelay(100)
    el_tracker.setOfflineMode()

    # Final instructions
    pylink.flushGetkeyQueue()
    display_instructions(ending_instructions,screen)

    return reaction_times

