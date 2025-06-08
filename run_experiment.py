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

from EyeTracking.EyeTrackingSetup import setup_and_calibrate_tracker
import argparse

def close_tracker(el_tracker: pylink.EyeLink, edf_filename: str, destination_path: str = "results"):
    """
    Close the tracker connection and download the EDF file.

    Parameters:
    - el_tracker: the EyeLink tracker object
    - edf_filename: filename used when calling openDataFile (e.g., "TASK1.EDF")
    - destination_path: folder where the EDF file should be saved
    """
    if el_tracker is not None and el_tracker.isConnected():
        el_tracker.setOfflineMode()
        pylink.msecDelay(500)  # give it time to enter offline mode
        el_tracker.closeDataFile()
        el_tracker.receiveDataFile(edf_filename, os.path.join(destination_path, edf_filename))
        el_tracker.close()

    # Close the graphics environment to allow future setup
    pylink.closeGraphics()


parser = argparse.ArgumentParser(description="Run experiment with optional dummy mode.")
parser.add_argument('--dummy', action='store_true', help='Run EyeLink in dummy mode')
args = parser.parse_args()
dummy_mode = args.dummy
print(f"Running in dummy mode: {dummy_mode}")

# el_tracker, edf_filename = setup_and_calibrate_tracker("MOT", dummy_mode=dummy_mode)
# main_mot_experiment(el_tracker)
# close_tracker(el_tracker, edf_filename)


# el_tracker, edf_filename = setup_and_calibrate_tracker("REACTION", dummy_mode=dummy_mode)
# main_abrupt_onset_experiment(el_tracker)
# close_tracker(el_tracker, edf_filename)


# el_tracker, edf_filename = setup_and_calibrate_tracker("SEARCH", dummy_mode=dummy_mode)
# main_visual_search_experiment(el_tracker)
# close_tracker(el_tracker, edf_filename)


el_tracker, edf_filename = setup_and_calibrate_tracker("GAME", dummy_mode=dummy_mode)
main_italian_game_experiment(el_tracker)
close_tracker(el_tracker, edf_filename)
