
import math
import random
import tkinter as tk
import pygame
import argparse
import os
import pylink
from bidi.algorithm import get_display
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
print(f"Screen dimensions: {WIDTH}x{HEIGHT}")

DISPLAY_SIZE_MULTIPLIER = 1.75
# Colors
WHITE, RED, GREEN, BLACK = (255,255,255), (255,0,0), (0,255,0), (0,0,0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
parser = argparse.ArgumentParser(description="Run experiment with optional dummy mode.")
parser.add_argument('--dummy', action='store_true', help='Run EyeLink in dummy mode')
args = parser.parse_args()
DUMMY_MODE = args.dummy

MOUSE_POS_MSG = "!MOUSE_POS"
WALDO_FOLDER = "stimulus/VisualSearch/waldo_images/"
instruction_font = pygame.font.Font("stimulus/instructions/hebrew_font.ttf", int(40  * DISPLAY_SIZE_MULTIPLIER)) 


    
def generate_grid_positions(n_items, jitter=True):
    aspect_ratio = WIDTH / HEIGHT
    cols = math.ceil(math.sqrt(n_items * aspect_ratio))
    rows = math.ceil(n_items / cols)

    cell_w = WIDTH / cols
    cell_h = HEIGHT / rows

    grid_positions = []
    for r in range(rows):
        for c in range(cols):
            if len(grid_positions) >= n_items:
                break
            x = c * cell_w + cell_w / 2
            y = r * cell_h + cell_h / 2
            if jitter:
                x += random.uniform(-cell_w * 0.25, cell_w * 0.25)
                y += random.uniform(-cell_h * 0.25, cell_h * 0.25)
            grid_positions.append((int(x), int(y)))
    random.shuffle(grid_positions)
    return grid_positions


def drift_correction(el_tracker: pylink.EyeLink) -> int:
    """
    Binocular drift-correction wrapper for EyeLink 1000.
    Never raises; returns the numeric result that EyeLink itself provides.

        0   success
       27   ESC pressed – tracker entered Setup (because allowSetup=1)
       -1   timeout / tracking error
       -2   SDK or I/O exception caught locally

    The calling code can decide what to do with the return value
    (e.g. retry, quick recalibration, or abort the trial).
    """
    if DUMMY_MODE:           # simulated connection
        return 0

    # 1  stop any current recording cleanly
    if el_tracker.isRecording():
        el_tracker.stopRecording()
        pylink.pumpDelay(50)

    # 2  switch to idle so drift-correction is accepted
    el_tracker.setOfflineMode()
    pylink.pumpDelay(50)

    # 3  run drift-correction at screen centre
    try:
        result = el_tracker.doDriftCorrect(
            WIDTH // 2, HEIGHT // 2,
            1,            # EyeLink draws the fixation dot
            1       # ESC opens full Setup/Camera screen
        )                       # returns 0 (OK) or 27 (ESC) :contentReference[oaicite:3]{index=3}
        if result == 0:
            el_tracker.applyDriftCorrect()  # apply the correction

    except Exception as exc:    # network or SDK glitch
        el_tracker.sendMessage(f"PY_DRIFTCORR_EXCEPTION {exc}")
        result = -2

    # 4  always restart recording so the next trial has eye data
    el_tracker.startRecording(1, 1, 1, 1)
    pylink.pumpDelay(100)

    # 5  log non-zero outcomes for later inspection
    if result != 0:
        el_tracker.sendMessage(f"DRIFTCORR_RESULT {result}")

    return result



def show_explanation_screen(images):
    """Display the instruction screens with navigation and start the game on Enter at the last screen.

    Args:
        images (list): A list of Pygame surface objects representing instruction images.
    """
    current_page = 0
    total_pages = len(images)

    while True:
        screen.blit(images[current_page], (0, 0))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if (event.key == pygame.K_LEFT or event.key ==  pygame.K_KP_4)  and current_page < total_pages - 1:
                    current_page += 1
                elif (event.key == pygame.K_RIGHT or event.key ==  pygame.K_KP_6) and current_page > 0:
                    current_page -= 1
                elif (event.key == pygame.K_RETURN or event.key ==  pygame.K_KP_ENTER) and current_page == total_pages - 1:
                    return
                

def display_instructions(lines,screen, waldo_image=False):
    pygame.event.clear()
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

   
    screen.fill(WHITE)
    y_offset = 100 * DISPLAY_SIZE_MULTIPLIER  # Start position for the first line
    for logical in lines:
        visual = get_display(logical)        # <- line 1: reorder for RTL/BiDi
        surf   = instruction_font.render(visual, True, (0, 0, 0))
        x      = screen.get_width() - surf.get_width() - 50 * DISPLAY_SIZE_MULTIPLIER
        screen.blit(surf, (x, y_offset))
        y_offset += 80 * DISPLAY_SIZE_MULTIPLIER

    if waldo_image:
                    # Load and display example Waldo image
                    example_path = os.path.join(WALDO_FOLDER, "waldo_example.png")
                    if os.path.exists(example_path):
                        waldo_img = pygame.image.load(example_path).convert_alpha()
                        # Scale to width = 200 px
                        w_ratio = 200 * DISPLAY_SIZE_MULTIPLIER / waldo_img.get_width()
                        new_size = (200 * DISPLAY_SIZE_MULTIPLIER, int(waldo_img.get_height() * w_ratio))
                        waldo_img = pygame.transform.scale(waldo_img, new_size)

                        # Blit to bottom center
                        screen.blit(waldo_img, (WIDTH//2 - new_size[0]//2, HEIGHT - new_size[1] - 50))
                    else:
                        print("Example Waldo image not found at", example_path)

    pygame.display.flip()
    wait_for_keypress()


