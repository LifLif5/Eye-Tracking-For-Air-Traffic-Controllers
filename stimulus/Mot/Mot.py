import pygame
import random
import numpy as np
import tkinter as tk
import yaml
import os
import pylink
from MouseMovements.MouseTracker import MouseRecorder
from ..Utils import generate_grid_positions, drift_correction
from ..Utils import HEIGHT,WIDTH,WHITE, RED, GREEN, BLACK, YELLOW, DUMMY_MODE,MOUSE_POS_MSG, DISPLAY_SIZE_MULTIPLIER


# Init pygame
pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Multi-Object Tracking (MOT)")
font = pygame.font.SysFont(None, int(40 * DISPLAY_SIZE_MULTIPLIER))

BALL_RADIUS = int(20 * DISPLAY_SIZE_MULTIPLIER)


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
                
# Load or initialize config
CONFIG_PATH = "stimulus\\MOT\\mot_config.yaml"
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
else:
    combos = [
    (15, 4, 7, 7),   
    (17, 4, 7, 7),
    (19, 4, 7, 7),
    (21, 4, 7, 7),
    (23, 4, 7, 7),
    (15, 5, 7, 7),
    (17, 5, 7, 7),
    (15, 6, 7, 7),
    (17, 6, 7, 7),
    (15, 7, 7, 7),
    (17, 7, 7, 7),
    (17, 4, 7, 7)   
    ]

    config = {
        "trials": [
            {"params": [num_objects, targets, duration, speed],
            "locations": None, "directions": None, "targets": None}
            for (num_objects, targets, duration, speed) in combos
            for _ in range(1)          # TODO 3 trials each
        ]
    }

def save_config():
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f)

def quit_check(events):
    for event in events:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            raise SystemExit("Experiment terminated by user.")

def mot_trial(el_tracker : pylink.EyeLink, trial_index):
    trial = config["trials"][trial_index]
    num_objects, num_targets, trial_duration, speed= trial["params"]
    speed = int(speed * DISPLAY_SIZE_MULTIPLIER)  # Scale speed for display size
    # Generate if None
    if not trial["locations"]:
        trial["locations"] = [list(pos) for pos in generate_grid_positions(num_objects, jitter=True)]
    if not trial["directions"]:
        trial["directions"] = np.random.uniform(-1, 1, (num_objects, 2)).tolist()
    if not trial["targets"]:
        trial["targets"] = random.sample(range(num_objects), num_targets)

    # Normalize directions
    dirs = []
    for d in trial["directions"]:
        v = np.array(d)
        v = v / np.linalg.norm(v) * speed
        dirs.append(v.tolist())

    objects = [{"pos": list(pos), "dir": dir[:]} for pos, dir in zip(trial["locations"], dirs)]
    target_indices = trial["targets"]

    save_config()  # Save any newly created values

    el_tracker.sendMessage(f"TRIALID {trial_index}")
    el_tracker.sendMessage(f"TRIAL_START {trial_index}")

    # Display initial targets AFTER recording has started
    screen.fill(BLACK)
    for i, obj in enumerate(objects):
        color = RED if i in target_indices else WHITE
        pygame.draw.circle(screen, color, obj["pos"], BALL_RADIUS)
    pygame.display.flip()

    # pygame.image.save(screen, "mot1.png") 
    el_tracker.sendMessage("TARGETS_APEAR")

    pygame.time.wait(2000)

    el_tracker.sendMessage("MOVEMENT_START")


    # Movement phase
    running = True
    # image_taken = False
    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()
    while running:
        events = pygame.event.get()
        quit_check(events)
        screen.fill(BLACK)
        for obj in objects:
            obj["pos"][0] += int(obj["dir"][0])
            obj["pos"][1] += int(obj["dir"][1])
            if obj["pos"][0] <= BALL_RADIUS or obj["pos"][0] >= WIDTH - BALL_RADIUS:
                obj["dir"][0] *= -1
            if obj["pos"][1] <= BALL_RADIUS or obj["pos"][1] >= HEIGHT - BALL_RADIUS:
                obj["dir"][1] *= -1
            pygame.draw.circle(screen, WHITE, obj["pos"], BALL_RADIUS)

            # # Draw arrow to indicate direction
            # pos = np.array(obj["pos"])
            # dir_vec = np.array(obj["dir"])
            # norm_dir = dir_vec / np.linalg.norm(dir_vec) if np.linalg.norm(dir_vec) != 0 else dir_vec
            # arrow_length = radius + 50
            # end_pos = pos + norm_dir * arrow_length
            # pygame.draw.line(screen, GREEN, pos, end_pos.astype(int), 3)
            # # Draw arrowhead
            # angle = np.arctan2(norm_dir[1], norm_dir[0])
            # arrowhead_length = 20
            # arrowhead_angle = np.pi / 6
            # left = end_pos - arrowhead_length * np.array([np.cos(angle - arrowhead_angle), np.sin(angle - arrowhead_angle)])
            # right = end_pos - arrowhead_length * np.array([np.cos(angle + arrowhead_angle), np.sin(angle + arrowhead_angle)])
            # pygame.draw.line(screen, GREEN, end_pos.astype(int), left.astype(int), 3)
            # pygame.draw.line(screen, GREEN, end_pos.astype(int), right.astype(int), 3)

        pygame.display.flip()
        x, y = pygame.mouse.get_pos()
        el_tracker.sendMessage(f"{MOUSE_POS_MSG} {x} {y}")
        # if not image_taken:
        #     pygame.image.save(screen, "mot2.png")
        #     image_taken = True
        clock.tick(30)
        if pygame.time.get_ticks() - start_time > trial_duration * 1000:
            running = False

    # Prompt
    text = font.render('Click on the targets!', True, GREEN)
    screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    pygame.display.flip()

    el_tracker.sendMessage("MOVEMENT_STOPPED")
    # pygame.image.save(screen, "mot3.png")
 

    # Click phase
    clicked, count = [], 0
    collecting = True
    pygame.event.clear()

    while collecting:
        events = pygame.event.get()
        quit_check(events)
        mouse_x, mouse_y = pygame.mouse.get_pos()
        el_tracker.sendMessage(f"{MOUSE_POS_MSG} {mouse_x} {mouse_y}")
        for event in events:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                el_tracker.sendMessage(f"!LEFT_MOUSE_UP {mouse_x} {mouse_y}")
            if event.type == pygame.MOUSEBUTTONDOWN:
                el_tracker.sendMessage(f"!LEFT_MOUSE_DOWN {mouse_x} {mouse_y}")  # Send left click position to EyeLink tracker


                for i, obj in enumerate(objects):
                    if i in clicked:
                        continue
                    if np.linalg.norm(np.array(obj["pos"]) - (mouse_x, mouse_y)) <= BALL_RADIUS:
                        clicked.append(i)
                        count += 1

                        # Indicate selection with yellow circle
                        pygame.draw.circle(screen, YELLOW, obj["pos"], BALL_RADIUS)
                        pygame.display.flip()
                        
                if count >= num_targets:
                    el_tracker.sendMessage("CLICKS_COLLECTED")

                    # Now reveal correctness
                    for i in clicked:
                        mark = 'V' if i in target_indices else 'X'
                        color = GREEN if mark == 'V' else RED
                        screen.blit(font.render(mark, True, color), font.render(mark, True, color).get_rect(center=objects[i]["pos"]))
                    
                    pygame.display.flip()
                    pygame.time.wait(2000)  
                    collecting = False
        clock.tick(30)

    # Show score
    score = len(set(clicked) & set(target_indices))
    screen.fill(BLACK)
    result = font.render(f'Your score: {score}/{num_targets}', True, WHITE)
    screen.blit(result, result.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    pygame.display.flip()
    pygame.time.wait(1000)
    el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_OK)
    return (score, num_targets)

    


def main_mot_experiment():
    performance = []
    try:
        el_tracker = pylink.getEYELINK()
        instruction_images = [
            pygame.image.load("stimulus/instructions/mot_instructions_page_1.png"),
            pygame.image.load("stimulus/instructions/mot_instructions_page_2.png")
        ]
        instruction_images = [pygame.transform.scale(img, (WIDTH, HEIGHT)) for img in instruction_images]
        show_explanation_screen(instruction_images)
        el_tracker.setOfflineMode()
        el_tracker.startRecording(1, 1, 1, 1)
        pylink.pumpDelay(100)  # allow tracker to stabilize
        for i in range(len(config["trials"])):
        # for i in range(5):
            drift_correction(el_tracker)
            performance.append(mot_trial(el_tracker, i))

        pylink.pumpDelay(100)
        el_tracker.stopRecording()
        return performance
    except SystemExit:
        pass
