
import pygame


from . import CommonConsts as Consts
##################################################################################
############################  Load assets  #######################################
background_image = pygame.image.load("stimulus/ItalianGame/pictures/background.png")  
background_image = pygame.transform.scale(background_image, (Consts.WIDTH, Consts.HEIGHT))  # Scale to fit the screen
home_base_image = pygame.image.load("stimulus/ItalianGame/pictures/House.png") 
home_base_image = pygame.transform.scale(home_base_image, Consts.HOUSE_IMAGE_SIZE)

# Load animal images
animals_images = {
    "Tralalero_Tralala": pygame.image.load("stimulus/ItalianGame/pictures/Tralalero_Tralala.png"),
    "Tung_Tung_Sahur": pygame.image.load("stimulus/ItalianGame/pictures/Tung_Tung_Sahur.png"),
    "Chimpanzini_Bananini": pygame.image.load("stimulus/ItalianGame/pictures/Chimpanzini_Bananini.png")
}

# Scale animal images
for key in animals_images:
    animals_images[key] = pygame.transform.scale(animals_images[key], Consts.ANIMAL_IMAGE_SIZE)

# Load and scale weapon images
Bombardino_Crocodillo_image = pygame.image.load("stimulus/ItalianGame/pictures/Bombardino_Crocodillo.png")
Bombardino_Crocodillo_image = pygame.transform.scale(Bombardino_Crocodillo_image, Consts.WEAPON_IMAGE_SIZE)

Bombini_Gusini_image = pygame.image.load("stimulus/ItalianGame/pictures/Bombini_Gusini.png")
Bombini_Gusini_image = pygame.transform.scale(Bombini_Gusini_image,  Consts.WEAPON_IMAGE_SIZE)  # Adjust size as needed

# Load explanation image
explanation_image = pygame.image.load("stimulus/ItalianGame/pictures/House.png")
explanation_image = pygame.transform.scale(explanation_image, (Consts.WIDTH, Consts.HEIGHT))  # Scale to fit the screen

# Load instruction images
instruction_images = [
    pygame.image.load("stimulus/instructions/game_instructions_page_1.png"),
    pygame.image.load("stimulus/instructions/game_instructions_page_2.png"),
    pygame.image.load("stimulus/instructions/game_instructions_page_3.png"),
    pygame.image.load("stimulus/instructions/game_instructions_page_4.png"),
    pygame.image.load("stimulus/instructions/game_instructions_page_5.png"),
    pygame.image.load("stimulus/instructions/game_instructions_page_6.png")
]
instruction_images = [pygame.transform.scale(img, (Consts.WIDTH, Consts.HEIGHT)) for img in instruction_images]

# Load gun sound
gun_sound = pygame.mixer.Sound("stimulus/ItalianGame/sounds/gun_sound.wav")  # Ensure the file path is correct

# Load activation stimulus/ItalianGame/sounds
bombardino_activation_sound = pygame.mixer.Sound("stimulus/ItalianGame/sounds/bombardino_crocodilo.wav")  # Ensure the file path is correct
bombini_activation_sound = pygame.mixer.Sound("stimulus/ItalianGame/sounds/bombini_gusini.wav")  # Ensure the file path is correct

# Load beep sound
beep_sound = pygame.mixer.Sound("stimulus/ItalianGame/sounds/beep.wav") 