
import math
import pygame
import random
import time
from .Spline import Spline
import pylink

from . import CommonConsts as Consts
from .Animal import Animal, Weapon, randomize_animal_location
from typing import List
from . import AssetLoader as Assets
import json

filename = "stimulus/ItalianGame/animal_trials.json"
def generate_trials(n_trials=5, trial_size=200, k=4):
    rng = random.Random()  # Ensures better randomness
    end_point = (
                Consts.HOME_BASE_POS[0] + Consts.HOUSE_IMAGE_SIZE[0] // 2,
                Consts.HOME_BASE_POS[1] + Consts.HOUSE_IMAGE_SIZE[1] // 2
            )
    trials = []
    for _ in range(n_trials):
        trial_animals = []
        trial_labels = []
        trial_points = []


        for _ in range(trial_size):
            animal_type = rng.choice(list(Assets.animals_images.keys()))
            spawn_x, spawn_y = randomize_animal_location()
            spline_seed = rng.randint(0, 2**31 - 1)

            spline = {
                "start": [round(spawn_x, 2), round(spawn_y, 2)],
                "end": end_point,
                "seed": spline_seed
            }
            trial_animals.append({
                "animal_type": animal_type,
                "spawn": [round(spawn_x, 2), round(spawn_y, 2)],
                "spline": spline
            })

            trial_labels.append(rng.randint(1, k))

            random_point = [round(rng.uniform(0, 1000), 2), round(rng.uniform(0, 1000), 2)]
            trial_points.append(random_point)

        trials.append({
            "animals": trial_animals,
            "labels": trial_labels,
            "points": trial_points
        })

    with open(filename, "w") as f:
        json.dump(trials, f, indent=2)

def get_animal(trial_number, index) -> Animal:
    with open(filename, "r") as f:
        trials = json.load(f)

    animal_data = trials[trial_number]["animals"][index]
    animal_type = animal_data["animal_type"]
    spawn = tuple(animal_data["spawn"])

    spline_data = trials[trial_number]["animals"][index]["spline"]
    spline_obj = Spline.create(tuple(spline_data["start"]), tuple(spline_data["end"]), seed=spline_data["seed"])
    
    image = Assets.animals_images[animal_type]

    return Animal.create(animal_type, image, spawn[0], spawn[1], spline_obj)

def is_time_to_distruct(trial_number, index) -> tuple[bool, tuple]:
    with open(filename, "r") as f:
        trials = json.load(f)
    point = tuple(trials[trial_number]["points"][index])
    is_time_to_distruct =trials[trial_number]["labels"][index] == 1
    return is_time_to_distruct, point