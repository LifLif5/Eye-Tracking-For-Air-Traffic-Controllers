import math
import pygame
import random
import time

import pylink

from .config_builder import generate_trials, get_animal, is_time_to_distruct

from . import CommonConsts as Consts
from .Animal import Animal, Weapon
from typing import List
from . import AssetLoader as Assets
from ..Utils import show_explanation_screen, drift_correction, HEIGHT,WIDTH, WHITE, BLACK, RED, BLUE, GREEN, DUMMY_MODE,MOUSE_POS_MSG, DISPLAY_SIZE_MULTIPLIER




# Initialize Pygame
pygame.init()

animal_circle_radius = Consts.ANIMALS_CIRCLE_RADIUS  # Radius of the animal circle
 
# Game window
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Eye Tracking Experiment")



# Font for displaying health
font = pygame.font.Font(None, Consts.FONT_SIZE)


def update_weapon_status(weapon: Weapon) -> None:
    """Deactivate the weapon if its active time has expired or ammo is 0."""
    if weapon.is_active:
        current_time = pygame.time.get_ticks()
        if current_time - weapon.activated_at >= weapon.maximum_time_active or weapon.ammo <= 0:
            weapon.deactivate()

# Initialize weapons
Bombardino_Crocodillo = Weapon(name="Bombardino_Crocodillo", ammo=10, cooldown=10000, maximum_time_active=10000, range=Consts.BOMBARDINO_CROCODILO_RANGE)
Bombini_Gusini = Weapon(name="Bombini_Gusini", ammo=5, cooldown=5000, maximum_time_active=10000, range= Consts.BOMBINI_GUSINI_RANGE)

def draw_object(image: pygame.Surface, x: float, y: float) -> None:
    screen.blit(image, (x, y))


def draw_circles_around_home_base() -> None:
    """Draw two red circles with different radii around the home base."""
    center_x, center_y = Consts.HOME_BASE_POS[0] + Consts.HOUSE_IMAGE_SIZE[0] // 2, Consts.HOME_BASE_POS[1] + Consts.HOUSE_IMAGE_SIZE[1] // 2

    # Ensure circles are drawn within screen boundaries
    if 0 <= center_x <= WIDTH and 0 <= center_y <= HEIGHT:
        pygame.draw.circle(screen, GREEN, (center_x, center_y), Bombardino_Crocodillo.range, 2)  # Outer circle for Bombardino_Crocodillo
        pygame.draw.circle(screen, GREEN, (center_x, center_y), Bombini_Gusini.range, 2)  # Inner circle for Bombini_Gusini
        pygame.draw.circle(screen, RED, (center_x, center_y), Consts.HOME_BASE_BOUNDARY_RADIUS, 2)  # Boundary circle for home base


def draw_animal(animal: Animal, show_image: bool) -> None:
    """Draw the animal as a black circle or its image based on the show_image flag."""
    if show_image:
        # Adjust the image position to align with the circle's center
        draw_object(animal.image, animal.x - animal_circle_radius, animal.y - animal_circle_radius)
    else:
        pygame.draw.circle(screen, BLUE, (int(animal.x + animal_circle_radius), int(animal.y + animal_circle_radius)), animal_circle_radius)

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

def prompt_numeric_input(screen, font, question_text, position=(750 * DISPLAY_SIZE_MULTIPLIER, 800 * DISPLAY_SIZE_MULTIPLIER)):
    input_text = ""
    active = True

    question_surface = font.render(question_text, True, BLACK)

    while active:
        # Draw the question
        screen.blit(question_surface, position)

        # Draw the input box
        input_box = pygame.Rect(position[0], position[1] + 40 * DISPLAY_SIZE_MULTIPLIER, 200 * DISPLAY_SIZE_MULTIPLIER, 36 * DISPLAY_SIZE_MULTIPLIER)
        pygame.draw.rect(screen, (200, 200, 200), input_box)
        text_surface = font.render(input_text, True, BLACK)
        screen.blit(text_surface, (input_box.x + 5 * DISPLAY_SIZE_MULTIPLIER, input_box.y + 5 *  DISPLAY_SIZE_MULTIPLIER))
        pygame.draw.rect(screen, BLACK, input_box, 2)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None  # Preserve quit behaviour
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    # Empty input → −1, otherwise convert to int
                    return -1 if input_text == "" else int(input_text)
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isdigit():
                    input_text += event.unicode

#####################################################################
def game_round(trial_index, el_tracker: pylink.EyeLink, beep_distractions: bool = False, visual_distractions: bool = False):

    take_image = False
    draw_red_circle_time = None
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

    clock = pygame.time.Clock()  # Create a clock to control the frame rate
    while running and (seconds_counter <Consts.NUMBER_OF_ANIMALS_IN_TRIAL or len(animals) != 0):
        screen.blit(Assets.background_image, (0, 0))  # Draw background
        screen.blit(Assets.home_base_image, Consts.HOME_BASE_POS)  # Draw home base
        draw_circles_around_home_base()  # Draw the circles

        # Update weapon statuses
        update_weapon_status(Bombardino_Crocodillo)
        update_weapon_status(Bombini_Gusini)

        # Display weapon images if active
        if Bombardino_Crocodillo.is_active:
            draw_weapon(Assets.Bombardino_Crocodillo_image, Consts.HOME_BASE_POS[0], Consts.HOME_BASE_POS[1] + 50 * DISPLAY_SIZE_MULTIPLIER)  # Adjust position
        if Bombini_Gusini.is_active:
            draw_weapon(Assets.Bombini_Gusini_image, Consts.HOME_BASE_POS[0], Consts.HOME_BASE_POS[1] - 80 * DISPLAY_SIZE_MULTIPLIER)  # Adjust position

        # Display player's health
        health_text = font.render(f"Health: {player_health}", True, WHITE)  # Changed color to white
        screen.blit(health_text, (WIDTH * 0.45, 10 * DISPLAY_SIZE_MULTIPLIER))

        # display weapon cooldowns
        bombardino_cooldown = max(0, Bombardino_Crocodillo.cooldown - (pygame.time.get_ticks() - Bombardino_Crocodillo.last_used))
        bombini_cooldown = max(0, Bombini_Gusini.cooldown - (pygame.time.get_ticks() - Bombini_Gusini.last_used))
        bombardino_cooldown_text = font.render(f"Crocodilo Cooldown: {bombardino_cooldown / 1000:.1f} seconds", True, WHITE)
        screen.blit(bombardino_cooldown_text, (10 * DISPLAY_SIZE_MULTIPLIER, 10 * DISPLAY_SIZE_MULTIPLIER))
        bombini_cooldown_text = font.render(f"Gusini Cooldown: {bombini_cooldown / 1000:.1f} seconds", True, WHITE)
        screen.blit(bombini_cooldown_text, (10 * DISPLAY_SIZE_MULTIPLIER, 50 * DISPLAY_SIZE_MULTIPLIER))

        # display weapon ammo
        bombardino_ammo_text = font.render(f"Crocodilo Ammo: {Bombardino_Crocodillo.ammo}", True, WHITE)
        screen.blit(bombardino_ammo_text, (WIDTH* 0.85, 10 * DISPLAY_SIZE_MULTIPLIER))
        bombini_ammo_text = font.render(f"Gusini Ammo: {Bombini_Gusini.ammo}", True, WHITE)
        screen.blit(bombini_ammo_text, (WIDTH* 0.85, 50 * DISPLAY_SIZE_MULTIPLIER))
        

        # # Display weapon ammo and status
        # Crocodillo_status = "Active" if Bombardino_Crocodillo.is_active else "Inactive"
        # Gusini_status = "Active" if Bombini_Gusini.is_active else "Inactive"
        # Crocodillo_text = font.render(f"Crocodillo Ammo: {Bombardino_Crocodillo.ammo} ({Crocodillo_status})", True, WHITE)
        # Gusini_text = font.render(f"Gusini Ammo: {Bombini_Gusini.ammo} ({Gusini_status})", True, WHITE)
        # screen.blit(Crocodillo_text, (10, 50))
        # screen.blit(Gusini_text, (10, 90))

        if draw_red_circle_time is not None:
            current_time = pygame.time.get_ticks()
            if current_time - draw_red_circle_time < Consts.RED_CIRCLE_DURATION:
                # Draw the red circle distraction
                pygame.draw.circle(screen, RED, (visual_x, visual_y), Consts.RED_CIRCLE_RADIUS)  # Red circle as distraction

            else:
                draw_red_circle_time = None

        # Check if player's health is 0 or less
        if player_health <= 0:
            running = False
            break
        mouse_x, mouse_y = pygame.mouse.get_pos()
        el_tracker.sendMessage(f"{MOUSE_POS_MSG} {mouse_x} {mouse_y}")

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Exit the game with ESC key
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            # every second spawn an animal and check for distractions
            if event.type == pygame.USEREVENT:
                next_animal = get_animal(trial_index, seconds_counter)
                if next_animal is None:
                    continue
                animals.append(next_animal)  # Get the next animal from the trial data

                should_distruct, distruct_position = is_time_to_distruct(trial_index, seconds_counter)
                if should_distruct:
                    if beep_distractions:
                        Assets.beep_sound.play()
                        beep_count += 1
                        el_tracker.sendMessage(f"BEEP {beep_count}")  # Send beep count to EyeLink tracker

                    if visual_distractions:  # Visual distraction event
                        visual_x, visual_y = distruct_position
                        pygame.draw.circle(screen, RED, (visual_x, visual_y), Consts.RED_CIRCLE_RADIUS)  # Red circle as distraction
                        visual_count += 1
                        draw_red_circle_time = pygame.time.get_ticks()  # Record the time when the red circle was drawn
                        el_tracker.sendMessage(f"VISUAL_DISTRACTION {visual_count} {visual_x} {visual_y}")  # Send visual distraction event to EyeLink tracker

                seconds_counter += 1  # Increment the seconds counter

            # Handle right mouse button press and release
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:  # Right mouse button
                right_mouse_pressed = True
                el_tracker.sendMessage(f"!RIGHT_MOUSE_DOWN {mouse_x} {mouse_y}")  # Send right click position to EyeLink tracker
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:  # Right mouse button released
                right_mouse_pressed = False
                el_tracker.sendMessage(f"!RIGHT_MOUSE_UP {mouse_x} {mouse_y}")  # Send right click release event to EyeLink tracker

            # Handle weapon activation
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_1 or event.key == pygame.K_KP1) :  # '1' key for Bombardino_Crocodillo
                el_tracker.sendMessage("BUTTON_1_PRESSED")  # Send button press event to EyeLink tracker
                if Bombardino_Crocodillo.activate():
                    Assets.bombardino_activation_sound.play()  # Play activation sound for Bombardino_Crocodillo
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_2 or event.key == pygame.K_KP2):  # '2' key for Bombini_Gusini
                el_tracker.sendMessage("BUTTON_2_PRESSED")  # Send button press event to EyeLink tracker
                if Bombini_Gusini.activate():
                    Assets.bombini_activation_sound.play()  # Play activation sound for Bombini_Gusini

            # Handle shooting with active weapons
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:  # Left mouse button for shooting
                # Prioritize Bombini_Gusini if both weapons are active and the click is within range
                el_tracker.sendMessage(f"!LEFT_MOUSE_DOWN {mouse_x} {mouse_y}")  # Send left click position to EyeLink tracker
                if Bombini_Gusini.is_active and shoot(Bombini_Gusini, mouse_x, mouse_y, animals):
                    pass  # Bombini_Gusini shoots, so Bombardino_Crocodillo does nothing
                elif Bombardino_Crocodillo.is_active:
                    shoot(Bombardino_Crocodillo, mouse_x, mouse_y ,animals)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                el_tracker.sendMessage(f"!LEFT_MOUSE_UP {mouse_x} {mouse_y}")

        # Move and draw animals
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
                take_image = True
            else:
                draw_animal(animal, show_image=False)

        # if take_image:
        #     # Take a screenshot of the current screen and save it with a timestamp
        #     pygame.image.save(screen, f"screenshot_{int(time.time() * 1000)}.png")
        #     take_image = False
            
        pygame.display.flip()
        clock.tick(30)
    # game finished
    # Display game over screen
    if player_health <= 0:
        el_tracker.sendMessage("GAME_OVER YOU_DIED")
        game_over_text = font.render("Game Over You Died", True, RED)  # Red color for game over text
    else:
        el_tracker.sendMessage("GAME_OVER YOU_WON")
        game_over_text = font.render("Game Over You Won", True, (0, 200, 0))  # Green color for victory text

    final_score_text = font.render(f"Tung Tung Kills: {tung_tung_kills}", True, BLACK)  # Black color for final score

    # Center the text on the screen
    game_over_x = (WIDTH - game_over_text.get_width()) // 2
    game_over_y = (HEIGHT - game_over_text.get_height()) // 2
    final_score_x = (WIDTH - final_score_text.get_width()) // 2
    final_score_y = game_over_y + game_over_text.get_height() + 20 * DISPLAY_SIZE_MULTIPLIER

    # Display the texts
    screen.fill(WHITE)  # White background
    screen.blit(game_over_text, (game_over_x, game_over_y))
    screen.blit(final_score_text, (final_score_x, final_score_y))
    pygame.display.flip()

    answer = 0
    if beep_distractions:
        answer = prompt_numeric_input(screen, font, "How many beeps were played?")

    elif visual_distractions:
        answer = prompt_numeric_input(screen, font, "How many red circles were shown?")

    else:
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN):
                    waiting = False
                
    # Send trial end message to EyeLink tracker
    el_tracker.sendMessage("TRIAL_RESULT %d" % pylink.TRIAL_OK)
    return (player_health,seconds_counter, tung_tung_kills,
             beep_count if beep_distractions else (visual_count if visual_distractions else 0), answer)


def main_italian_game_experiment():

    performance = []

    el_tracker = pylink.getEYELINK()
    generate_trials()  # Generate trials if needed
    # Call the explanation screen before starting the game loop
    show_explanation_screen(Assets.instruction_images[0:4])
    drift_correction(el_tracker)

    performance.append(game_round(0, el_tracker))
    pylink.pumpDelay(100)
    el_tracker.stopRecording()

    show_explanation_screen(Assets.instruction_images[4:5])
    drift_correction(el_tracker)
    performance.append(game_round(1, el_tracker, beep_distractions= True))
    pylink.pumpDelay(100)
    el_tracker.stopRecording()

    show_explanation_screen(Assets.instruction_images[5:6])
    drift_correction(el_tracker)
    performance.append(game_round(2, el_tracker, visual_distractions=True))
    pylink.pumpDelay(100)
    el_tracker.stopRecording()
    el_tracker.setOfflineMode()

    return performance