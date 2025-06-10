import math
import pygame
import random
import time

import pylink

from .config_builder import generate_trials, get_animal, is_time_to_distruct

from . import CommonConsts as Consts
from .Animal import Animal, Weapon, randomize_animal_location
from typing import List
from . import AssetLoader as Assets
from ..Utils import HEIGHT,WIDTH





# Initialize Pygame
pygame.init()

animal_circle_radius = Consts.ANIMALS_CIRCLE_RADIUS  # Radius of the animal circle
 
# Game window
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Eye Tracking Experiment")



# Font for displaying health
font = pygame.font.Font(None, Consts.FONT_SIZE)


def show_explanation_screen():
    """Display the instruction screens with navigation and start the game on Enter at the last screen."""
    current_page = 0
    while True:
        screen.blit(Assets.instruction_images[current_page], (0, 0))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT and current_page < len(Assets.instruction_images) - 1:  # Next page
                    current_page += 1
                elif event.key == pygame.K_RIGHT and current_page > 0:  # Previous page
                    current_page -= 1
                elif event.key == pygame.K_RETURN and current_page == len(Assets.instruction_images) - 1:  # Start game
                    return

def update_weapon_status(weapon: Weapon) -> None:
    """Deactivate the weapon if its active time has expired or ammo is 0."""
    if weapon.is_active:
        current_time = pygame.time.get_ticks()
        if current_time - weapon.activated_at >= weapon.maximum_time_active or weapon.ammo <= 0:
            weapon.deactivate()

# Initialize weapons
Bombardino_Crocodillo = Weapon(name="Bombardino_Crocodillo", ammo=10, cooldown=10000, maximum_time_active=10000, range=400)
Bombini_Gusini = Weapon(name="Bombini_Gusini", ammo=5, cooldown=5000, maximum_time_active=10000, range=250)

def draw_object(image: pygame.Surface, x: float, y: float) -> None:
    screen.blit(image, (x, y))


def draw_circles_around_home_base() -> None:
    """Draw two red circles with different radii around the home base."""
    center_x, center_y = Consts.HOME_BASE_POS[0] + Consts.HOUSE_IMAGE_SIZE[0] // 2, Consts.HOME_BASE_POS[1] + Consts.HOUSE_IMAGE_SIZE[1] // 2

    # Ensure circles are drawn within screen boundaries
    if 0 <= center_x <= WIDTH and 0 <= center_y <= HEIGHT:
        pygame.draw.circle(screen, (0, 255, 0), (center_x, center_y), Bombardino_Crocodillo.range, 2)  # Outer circle for Bombardino_Crocodillo
        pygame.draw.circle(screen, (0, 255, 0), (center_x, center_y), Bombini_Gusini.range, 2)  # Inner circle for Bombini_Gusini
        pygame.draw.circle(screen, (255, 0, 0), (center_x, center_y), Consts.HOME_BASE_BOUNDARY_RADIUS, 2)  # Boundary circle for home base


def draw_animal(animal: Animal, show_image: bool) -> None:
    """Draw the animal as a black circle or its image based on the show_image flag."""
    if show_image:
        # Adjust the image position to align with the circle's center
        draw_object(animal.image, animal.x - animal_circle_radius, animal.y - animal_circle_radius)
    else:
        pygame.draw.circle(screen, (0, 0, 255), (int(animal.x + animal_circle_radius), int(animal.y + animal_circle_radius)), animal_circle_radius)

def draw_weapon(image: pygame.Surface, x: float, y: float) -> None:
    """Draw the weapon image at the specified position."""
    screen.blit(image, (x, y))

def shoot(weapon: Weapon, mouse_x: int, mouse_y: int, animals : List[Animal]) -> bool:
    """Shoot the weapon if it's active, has ammo, and is within range. Returns True if it shoots."""
    global tung_tung_kills  # Declare tung_tung_kills as global
    if weapon.is_active:
        # Check if the target is within range
        center_x, center_y = Consts.HOME_BASE_POS[0] + Consts.HOUSE_IMAGE_SIZE[0] // 2, Consts.HOME_BASE_POS[1] + Consts.HOUSE_IMAGE_SIZE[1] // 2
        distance = math.sqrt((mouse_x - center_x) ** 2 + (mouse_y - center_y) ** 2)
        if distance > weapon.range:
            return False

        # Find the first animal clicked
        for animal in animals:
            if animal.is_clicked(mouse_x, mouse_y):
                animal.health -= 1
                if animal.health <= 0:
                    animals.remove(animal)
                    if animal.animal_type == "Tung_Tung_Sahur":
                        tung_tung_kills += 1
                weapon.ammo -= 1
                if weapon.ammo <= 0:
                    weapon.deactivate()
                Assets.gun_sound.play()  # Play gun sound on successful shot
                return True
    return False

def prompt_numeric_input(screen, font, question_text, position=(750, 650)):
    input_text = ""
    active = True

    # Pre-render the question text
    question_surface = font.render(question_text, True, (0, 0, 0))

    while active:
        screen.blit(question_surface, position)

        # Render input box
        input_box = pygame.Rect(position[0], position[1] + 40, 200, 36)
        pygame.draw.rect(screen, (200, 200, 200), input_box)
        text_surface = font.render(input_text, True, (0, 0, 0))
        screen.blit(text_surface, (input_box.x + 5, input_box.y + 5))
        pygame.draw.rect(screen, (0, 0, 0), input_box, 2)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None  # Exit condition
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return input_text  # Return the numeric string
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isdigit():
                    input_text += event.unicode


#####################################################################
def game_round(trial_index, el_tracker: pylink.EyeLink, beep_distractions: bool = False, visual_distractions: bool = False):
    # Initialize scoring system
    global player_health, tung_tung_kills
    player_health = Consts.INITIAL_PLAYER_HEALTH
    tung_tung_kills = 0
    seconds_counter = 0

    beep_count = 0
    visual_count = 0
    # reinitialize weapons
    Bombardino_Crocodillo.reinitialize()
    Bombini_Gusini.reinitialize()

    # List to store active animals
    animals: List[Animal] = []

    # Timer setup
    pygame.time.set_timer(pygame.USEREVENT, Consts.SPAWN_INTERVAL) 



    # Game loop
    running: bool = True
    right_mouse_pressed = False  # Track the state of the right mouse button
    el_tracker.sendMessage(f"TRIALID {trial_index}")
    el_tracker.sendMessage(f"TRIAL_START {trial_index}")
    while running:
        screen.blit(Assets.background_image, (0, 0))  # Draw background
        screen.blit(Assets.home_base_image, Consts.HOME_BASE_POS)  # Draw home base
        draw_circles_around_home_base()  # Draw the circles

        # Update weapon statuses
        update_weapon_status(Bombardino_Crocodillo)
        update_weapon_status(Bombini_Gusini)

        # Display weapon images if active
        if Bombardino_Crocodillo.is_active:
            draw_weapon(Assets.Bombardino_Crocodillo_image, Consts.HOME_BASE_POS[0], Consts.HOME_BASE_POS[1] + 50)  # Adjust position
        if Bombini_Gusini.is_active:
            draw_weapon(Assets.Bombini_Gusini_image, Consts.HOME_BASE_POS[0], Consts.HOME_BASE_POS[1] - 80)  # Adjust position

        # Display player's health
        health_text = font.render(f"Health: {player_health}", True, (255, 255, 255))  # Changed color to white
        screen.blit(health_text, (WIDTH * 0.45, 10))

        # display weapon cooldowns
        bombardino_cooldown = max(0, Bombardino_Crocodillo.cooldown - (pygame.time.get_ticks() - Bombardino_Crocodillo.last_used))
        bombini_cooldown = max(0, Bombini_Gusini.cooldown - (pygame.time.get_ticks() - Bombini_Gusini.last_used))
        bombardino_cooldown_text = font.render(f"Crocodilo Cooldown: {bombardino_cooldown / 1000:.1f} seconds", True, (255, 255, 255))
        screen.blit(bombardino_cooldown_text, (10, 10))
        bombini_cooldown_text = font.render(f"Gusini Cooldown: {bombini_cooldown / 1000:.1f} seconds", True, (255, 255, 255))
        screen.blit(bombini_cooldown_text, (10, 50))

        # display weapon ammo
        bombardino_ammo_text = font.render(f"Crocodilo Ammo: {Bombardino_Crocodillo.ammo}", True, (255, 255, 255))
        screen.blit(bombardino_ammo_text, (WIDTH* 0.8, 10))
        bombini_ammo_text = font.render(f"Gusini Ammo: {Bombini_Gusini.ammo}", True, (255, 255, 255))
        screen.blit(bombini_ammo_text, (WIDTH* 0.8, 50))
        

        # # Display weapon ammo and status
        # Crocodillo_status = "Active" if Bombardino_Crocodillo.is_active else "Inactive"
        # Gusini_status = "Active" if Bombini_Gusini.is_active else "Inactive"
        # Crocodillo_text = font.render(f"Crocodillo Ammo: {Bombardino_Crocodillo.ammo} ({Crocodillo_status})", True, (255, 255, 255))
        # Gusini_text = font.render(f"Gusini Ammo: {Bombini_Gusini.ammo} ({Gusini_status})", True, (255, 255, 255))
        # screen.blit(Crocodillo_text, (10, 50))
        # screen.blit(Gusini_text, (10, 90))


        # Check if player's health is 0 or less
        if player_health <= 0:
            running = False
            break

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Exit the game with ESC key
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            # every second spawn an animal and check for distractions
            if event.type == pygame.USEREVENT:
                animals.append(get_animal(trial_index, seconds_counter))  # Get the next animal from the trial data

                should_distruct, distruct_position = is_time_to_distruct(trial_index, seconds_counter)
                if should_distruct:
                    if beep_distractions:
                        Assets.beep_sound.play()
                        beep_count += 1

                    if visual_distractions:  # Visual distraction event
                        visual_x, visual_y = distruct_position
                        pygame.draw.circle(screen, (255, 0, 0), (visual_x, visual_y), 20)  # Red circle as distraction
                        visual_count += 1

                seconds_counter += 1  # Increment the seconds counter

            # Handle right mouse button press and release
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:  # Right mouse button
                right_mouse_pressed = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:  # Right mouse button released
                right_mouse_pressed = False

            # Handle weapon activation
            if event.type == pygame.KEYDOWN and event.key == pygame.K_c:  # 'c' key for Bombardino_Crocodillo
                if Bombardino_Crocodillo.activate():
                    Assets.bombardino_activation_sound.play()  # Play activation sound for Bombardino_Crocodillo
            if event.type == pygame.KEYDOWN and event.key == pygame.K_g:  # 'g' key for Bombini_Gusini
                if Bombini_Gusini.activate():
                    Assets.bombini_activation_sound.play()  # Play activation sound for Bombini_Gusini

            # Handle shooting with active weapons
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left mouse button for shooting
                mouse_x, mouse_y = pygame.mouse.get_pos()
                # Prioritize Bombini_Gusini if both weapons are active and the click is within range
                if Bombini_Gusini.is_active and shoot(Bombini_Gusini, mouse_x, mouse_y, animals):
                    pass  # Bombini_Gusini shoots, so Bombardino_Crocodillo does nothing
                elif Bombardino_Crocodillo.is_active:
                    shoot(Bombardino_Crocodillo, mouse_x, mouse_y ,animals)

        # Move and draw animals
        mouse_x, mouse_y = pygame.mouse.get_pos()
        for animal in animals:
            animal.move()  # Use the simplified movement logic

            # Check if the animal reaches the square around the home base
            home_base_center_x = Consts.HOME_BASE_POS[0] + Consts.HOUSE_IMAGE_SIZE[0] // 2
            home_base_center_y = Consts.HOME_BASE_POS[1] + Consts.HOUSE_IMAGE_SIZE[1] // 2
            animal_center_x = animal.x + animal_circle_radius  # Center of the animal
            animal_center_y = animal.y + animal_circle_radius  # Center of the animal

            # Calculate the distance between the centers
            distance = math.sqrt((home_base_center_x - animal_center_x) ** 2 + (home_base_center_y - animal_center_y) ** 2)

            # Check if the distance is less than or equal to the collision threshold
            if distance <= (animal_circle_radius + Consts.HOME_BASE_BOUNDARY_RADIUS):
                player_health -= animal.damage
                if player_health <= 0:
                    running = False
                animals.remove(animal)
                continue

            if right_mouse_pressed and animal.is_clicked(mouse_x, mouse_y):
                draw_animal(animal, show_image=True)
            else:
                draw_animal(animal, show_image=False)

        pygame.display.flip()
        pygame.time.delay(30)  # Smooth animation

    # game finished
    # Display game over screen
    game_over_text = font.render("Game Over", True, (255, 0, 0))  # Red color for game over text
    final_score_text = font.render(f"Tung Tung Kills: {tung_tung_kills}", True, (0, 0, 0))  # Black color for final score

    # Center the text on the screen
    game_over_x = (WIDTH - game_over_text.get_width()) // 2
    game_over_y = (HEIGHT - game_over_text.get_height()) // 2
    final_score_x = (WIDTH - final_score_text.get_width()) // 2
    final_score_y = game_over_y + game_over_text.get_height() + 20

    # Display the texts
    screen.fill((255, 255, 255))  # White background
    screen.blit(game_over_text, (game_over_x, game_over_y))
    screen.blit(final_score_text, (final_score_x, final_score_y))
    pygame.display.flip()

    if beep_distractions:
        value = prompt_numeric_input(screen, font, "How many beeps were played?")

    elif visual_distractions:
        value = prompt_numeric_input(screen, font, "How many red circles were shown?")

    else:
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN):
                    waiting = False
                
    # Send trial end message to EyeLink tracker
    el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_OK)


def main_italian_game_experiment(el_tracker:pylink.EyeLink):
    generate_trials()  # Generate trials if needed
    # Call the explanation screen before starting the game loop
    show_explanation_screen()
    el_tracker.setOfflineMode()
    el_tracker.startRecording(1, 1, 1, 1)
    pylink.pumpDelay(100)  # allow tracker to stabilize
    game_round(0, el_tracker)
    pylink.pumpDelay(100)
    el_tracker.stopRecording()

    show_explanation_screen()
    el_tracker.setOfflineMode()
    el_tracker.startRecording(1, 1, 1, 1)
    pylink.pumpDelay(100)  # allow tracker to stabilize
    game_round(1, el_tracker, beep_distractions= True)
    pylink.pumpDelay(100)
    el_tracker.stopRecording()

    show_explanation_screen()
    el_tracker.setOfflineMode()
    el_tracker.startRecording(1, 1, 1, 1)
    pylink.pumpDelay(100)  # allow tracker to stabilize
    game_round(2, el_tracker, visual_distractions=True)
    pylink.pumpDelay(100)
    el_tracker.stopRecording()
    el_tracker.setOfflineMode()
