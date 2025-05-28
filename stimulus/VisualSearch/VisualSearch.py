import pygame
import random
import sys
import time
import tkinter as tk
import math

from ..Utils import generate_grid_positions, HEIGHT,WIDTH,WHITE, RED, GREEN, BLACK ,BLUE

# Initialize pygame
pygame.init()

# Parameters
FONT_SIZE = 40
USE_NOISE = True  # Set to False for exact center, True for jittered

# Shapes
T_SHAPE = "T"
L_SHAPE = "L"

# Initialize screen
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Visual Search Task")
font = pygame.font.SysFont(None, FONT_SIZE, bold=True)

def draw_letter(letter, color, pos, angle=0):
    text_surface = font.render(letter, True, color)
    text_surface = pygame.transform.rotate(text_surface, angle)
    rect = text_surface.get_rect(center=(pos[0], pos[1]))
    screen.blit(text_surface, rect.topleft)



def search_trial(SEARCH_TYPE, N_DISTRACTORS):
    screen.fill(WHITE)
    focus_text = font.render("+", True, BLACK)
    focus_rect = focus_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(focus_text, focus_rect.topleft)
    pygame.display.flip()
    time.sleep(1)

    positions = generate_grid_positions(N_DISTRACTORS + 1, jitter=USE_NOISE)
    screen.fill(WHITE)
    target_pos = random.choice(positions)

    for pos in positions:
        if pos == target_pos:
            continue
        angle = random.choice([0, 90, 180, 270])
        if SEARCH_TYPE == "feature":
            draw_letter(L_SHAPE, BLACK, pos, angle)
        else:
            if random.random() < 0.5:
                draw_letter(L_SHAPE, BLUE, pos, angle)
            else:
                draw_letter(T_SHAPE, RED, pos, angle)

    if SEARCH_TYPE == "feature":
        draw_letter(T_SHAPE, BLACK, target_pos)
    else:
        target_type = random.choice([1, 2])
        if target_type == 1:
            draw_letter(T_SHAPE, BLUE, target_pos)
        else:
            draw_letter(L_SHAPE, RED, target_pos)

    pygame.display.flip()

    pygame.event.clear()
    start_time = time.time()
    while time.time() - start_time < 30:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                dist = ((x - target_pos[0]) ** 2 + (y - target_pos[1]) ** 2) ** 0.5
                if dist <= FONT_SIZE:
                    return time.time() - start_time
                else:
                    return 30 + time.time() - start_time
    return -1

def main_visual_search_experiment():
    performance = []
    num_trials = 1 #TODO 5
    num_distractors = [5]#[7,17,31, 65, 119, 189]TODO

    for distractors in num_distractors:
        for _ in range(num_trials):
            performance.append(search_trial("feature", distractors))
        for _ in range(num_trials):
            performance.append(search_trial("conjunction", distractors))
    print(performance)

