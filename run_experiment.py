import ctypes
ctypes.windll.user32.SetProcessDPIAware()  # Ensure high DPI awareness for Windows



from stimulus.Mot.Mot import main_mot_experiment
from stimulus.VisualSearch.VisualSearch import main_visual_search_experiment
from stimulus.AbruptOnset.AbruptOnset import main_abrupt_onset_experiment
from stimulus.ItalianGame.ItalianGame import main_italian_game_experiment
import time
from MouseMovements.MouseTracker import PygameMouseTracker
import pygame
import json
import pylink
import os
from stimulus import Utils

from EyeTracking.EyeTrackingSetup import setup_and_calibrate_tracker, terminate_task, set_dummy_mode_in_tracker
import argparse


parser = argparse.ArgumentParser(description="Run experiment with optional dummy mode.")
parser.add_argument('--dummy', action='store_true', help='Run EyeLink in dummy mode')
args = parser.parse_args()
dummy_mode = args.dummy
print(f"Running in dummy mode: {dummy_mode}")
set_dummy_mode_in_tracker(dummy_mode)


el_tracker, edf_filename = setup_and_calibrate_tracker("MOT")
mot_performance = main_mot_experiment()
terminate_task("MOT", mot_performance)


# el_tracker, edf_filename = setup_and_calibrate_tracker("REACTION")
# reaction_performance = main_abrupt_onset_experiment()
# terminate_task("REACTION", reaction_performance)


el_tracker, edf_filename = setup_and_calibrate_tracker("SEARCH")
visual_search_performance = main_visual_search_experiment()
terminate_task("SEARCH", visual_search_performance)


el_tracker, edf_filename = setup_and_calibrate_tracker("GAME")
italian_game_performance = main_italian_game_experiment()
terminate_task("GAME", italian_game_performance)


el_tracker.close()
pylink.closeGraphics()