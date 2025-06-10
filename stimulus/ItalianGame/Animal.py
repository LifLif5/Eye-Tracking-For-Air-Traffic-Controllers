import random
from typing import List, Tuple

import pygame
import scipy
from scipy.interpolate import splprep, splev, make_interp_spline
from ..Utils import HEIGHT,WIDTH

import numpy as np
from . import CommonConsts as Consts
import math
import pygame
from .Spline import Spline
class Animal:
    def __init__(self, animal_type, image, x, y, health=1, damage=0, spline=None):
        self.animal_type = animal_type
        self.image = image
        self.x = x
        self.y = y
        self.health = health
        self.damage = damage
        self.spline = spline

        # Create spline from current position to home base
        start = (self.x, self.y)
        end = (
            Consts.HOME_BASE_POS[0] + Consts.HOUSE_IMAGE_SIZE[0] // 2,
            Consts.HOME_BASE_POS[1] + Consts.HOUSE_IMAGE_SIZE[1] // 2
        )

    @classmethod
    def create(cls, animal_type: str, image: pygame.Surface,
                x: float, y: float, spline: Spline) -> "Animal":
        health = 3 if animal_type == "Tralalero_Tralala" else 2 if animal_type == "Chimpanzini_Bananini" else 1
        damage = 20 if animal_type == "Tralalero_Tralala" else 10 if animal_type == "Chimpanzini_Bananini" else 0
        return cls(animal_type, image, x, y, health, damage, spline)

    def move(self):
        self.x, self.y = self.spline.get_next(Consts.ANIMAL_SPEED)

    def is_clicked(self, mouse_x: int, mouse_y: int) -> bool:
        return self.x <= mouse_x <= self.x + 50 and self.y <= mouse_y <= self.y + 50

def randomize_animal_location() -> Tuple[int, int]:
    spawn_x: int = random.choice([0+Consts.ANIMALS_CIRCLE_RADIUS, WIDTH - Consts.ANIMALS_CIRCLE_RADIUS])
    spawn_y: int = random.randint(0+Consts.ANIMALS_CIRCLE_RADIUS, HEIGHT - Consts.ANIMALS_CIRCLE_RADIUS)
    return spawn_x, spawn_y


class Weapon:
    def __init__(self, name: str, ammo: int, cooldown: int, maximum_time_active: int, range: int):
        self.name = name
        self.ammo = ammo
        self.max_ammo = ammo
        self.cooldown = cooldown  # Cooldown in milliseconds
        self.maximum_time_active = maximum_time_active  # Maximum time the weapon can stay active in milliseconds
        self.range = range  # Maximum distance from the center where the weapon can shoot
        self.last_used = pygame.time.get_ticks() - cooldown  # Timestamp of the last use
        self.activated_at = None  # Timestamp when the weapon was activated
        self.is_active = False

    def activate(self) -> bool:
        """Activate the weapon if it's not on cooldown."""
        current_time = pygame.time.get_ticks()
        if not self.is_active and current_time - self.last_used >= self.cooldown:
            self.is_active = True
            self.ammo = self.max_ammo
            self.activated_at = current_time
            return True
        return False

    

    def deactivate(self) -> None:
        """Deactivate the weapon and start cooldown."""
        self.is_active = False
        self.last_used = pygame.time.get_ticks()

    def reinitialize(self) -> None:
        """restarts cooldown and ammo"""
        self.ammo = self.max_ammo
        self.last_used = pygame.time.get_ticks() - self.cooldown  # Timestamp of the last use
        self.activated_at = None
        self.is_active = False