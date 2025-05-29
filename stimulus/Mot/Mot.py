import pygame
import random
import numpy as np
import tkinter as tk
import yaml
import os
import pylink
from MouseMovements.MouseTracker import MouseRecorder
from ..Utils import generate_grid_positions, HEIGHT,WIDTH,WHITE, RED, GREEN, BLACK


# Init pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Multi-Object Tracking (MOT)")
font = pygame.font.SysFont(None, 40)


# Load or initialize config
CONFIG_PATH = "stimulus\MOT\mot_config.yaml"
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
else:
    config = {
    "trials": [{"params": list(p), "locations": None, "directions": None, "targets": None} for p in [
        [10, 4], [12, 4], [14, 4], [16, 4], [18, 4],
        [20, 4], [22, 4], [24, 4], [26, 4], [28, 4],
        [11, 5], [11, 5], [11, 5], [11, 5], [11, 5],
        [13, 6], [13, 6], [13, 6], [13, 6], [13, 6],
        [15, 7], [15, 7], [15, 7], [15, 7], [15, 7]
    ]]
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
    num_objects, num_targets = trial["params"]
    radius, speed = 20, 5

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
        pygame.draw.circle(screen, color, obj["pos"], radius)
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
            if obj["pos"][0] <= radius or obj["pos"][0] >= WIDTH - radius:
                obj["dir"][0] *= -1
            if obj["pos"][1] <= radius or obj["pos"][1] >= HEIGHT - radius:
                obj["dir"][1] *= -1
            pygame.draw.circle(screen, WHITE, obj["pos"], radius)

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
        # if not image_taken:
        #     pygame.image.save(screen, "mot2.png")
        #     image_taken = True
        clock.tick(30)
        if pygame.time.get_ticks() - start_time > 10000:
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
    #TODO mouse_tracker.start_trial(trial_index)

    while collecting:
        events = pygame.event.get()
        quit_check(events)
        # TODO mouse_tracker.update()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:

                # TODO mouse_tracker.log_event("click", {"pos": event.pos,
                #                              "button": event.button})
                mouse_pos = event.pos
                for i, obj in enumerate(objects):
                    if i in clicked: continue
                    if np.linalg.norm(np.array(obj["pos"]) - mouse_pos) <= radius:
                        clicked.append(i)
                        count += 1
                        mark = 'V' if i in target_indices else 'X'
                        color = GREEN if mark == 'V' else RED
                        screen.blit(font.render(mark, True, color), font.render(mark, True, color).get_rect(center=obj["pos"]))
                        pygame.display.flip()
                if count >= num_targets:
                    el_tracker.sendMessage("CLICKS_COLLECTED")

                    pygame.time.wait(500)
                    collecting = False
    # TODO mouse_tracker.stop_trial()
    # Show score
    score = len(set(clicked) & set(target_indices))
    screen.fill(BLACK)
    result = font.render(f'Your score: {score}/{num_targets}', True, WHITE)
    screen.blit(result, result.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    pygame.display.flip()
    pygame.time.wait(3000)
    el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_OK)

    


def main_mot_experiment(el_tracker):
    # Initialize mouse tracker
    # global mouse_tracker TODO
    # mouse_tracker = MouseRecorder(mouse_file_path)
    try:
        # for i in range(len(config["trials"])):
        #     mot_trial(i)
        el_tracker.setOfflineMode()
        el_tracker.startRecording(1, 1, 1, 1)
        pylink.pumpDelay(100)  # allow tracker to stabilize
        mot_trial(el_tracker, 0)

        pylink.pumpDelay(100)
        el_tracker.stopRecording()
    except SystemExit:
        pass