#
# Copyright (c) 1996-2024, SR Research Ltd., All Rights Reserved
#
# For use by SR Research licencees only. Redistribution and use in source
# and binary forms, with or without modification, are NOT permitted.
#
# Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in
# the documentation and/or other materials provided with the distribution.
#
# Neither name of SR Research Ltd nor the name of contributors may be used
# to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS ``AS
# IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# DESCRIPTION:
# This is a basic example, which shows how to connect to and disconnect from
# the tracker, how to open and close data file, how to start/stop recording,
# and the standard messages for integration with the Data Viewer software.
# Four pictures will be shown one-by-one, and each trial terminates upon a
# keypress response (the spacebar) or until 3 secs have elapsed.
#
# Last updated: 3/29/2021

from __future__ import division
from __future__ import print_function

import pylink
import os
import platform
import sys
import pygame
import random
import time
import json
from pygame.locals import *

from stimulus import Utils
from .CalibrationGraphicsPygame import CalibrationGraphics
from string import ascii_letters, digits

participant_name = ""
session_folder = ""
current_edf_file = ""
dummy_mode = False
def set_dummy_mode_in_tracker(mode: bool):
    """Set the dummy mode for the EyeLink tracker."""
    global dummy_mode
    dummy_mode = mode


def setup_and_calibrate_tracker(task_name) -> "pylink.EyeLink" : 
    global participant_name, session_folder, current_edf_file
    # initialize pygame
    pygame.init()
    win = pygame.display.set_mode((0, 0), FULLSCREEN | DOUBLEBUF)
    pygame.mouse.set_visible(False)  # hide mouse cursor

    # get the screen resolution natively supported by the monitor
    scn_width, scn_height = Utils.WIDTH, Utils.HEIGHT
    pygame.display.set_caption("Enter EDF filename")
    font = pygame.font.SysFont('Arial', 55)

    if participant_name == "":
        allowed_char = ascii_letters + digits + '_'
        active = True
        error_msg = ''
        
        while active:
            win.fill((128, 128, 128))

            prompt_lines = [
                'Enter participant name/Id (max 8 characters)',
                'Use only letters, numbers, and underscore',
                'Press ENTER when done'
            ]

            for i, line in enumerate(prompt_lines):
                line_surf = font.render(line, True, (0, 0, 0))
                win.blit(line_surf, (50, 50 + i * 70))

            input_surf = font.render('> ' + participant_name, True, (0, 0, 0))
            win.blit(input_surf, (50, 300))

            if error_msg:
                err_surf = font.render(error_msg, True, (200, 0, 0))
                win.blit(err_surf, (50, 400))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if not all(c in allowed_char for c in participant_name):
                            error_msg = 'ERROR: Invalid EDF filename'
                        elif len(participant_name) > 8:
                            error_msg = 'ERROR: Filename too long'
                        elif len(participant_name) == 0:
                            error_msg = 'ERROR: Filename required'
                        else:
                            active = False
                    elif event.key == pygame.K_BACKSPACE:
                        participant_name = participant_name[:-1]
                        error_msg = ''
                    else:
                        char = event.unicode
                        if char in allowed_char:
                            participant_name += char
                            error_msg = ''

    # Set up EDF data file name and local data folder
    #
    # The EDF data filename should not exceed eight alphanumeric characters
    # use ONLY number 0-9, letters, and _ (underscore) in the filename
    edf_fname = participant_name
    # Set up a folder to store the EDF data files and the associated resources
    # e.g., files defining the interest areas used in each trialer
    results_folder = 'results'
    if not os.path.exists(results_folder):
        os.makedirs(results_folder)
    participant_folder = os.path.join(results_folder, participant_name)
    if not os.path.exists(participant_folder):
        os.makedirs(participant_folder)
    # We download EDF data file from the EyeLink Host PC to the local hard
    # drive at the end of each testing session, here we rename the EDF to
    # include session start date/time
    time_str = time.strftime("_%Y_%m_%d_%H_%M", time.localtime())
    session_identifier =  task_name + "_" +edf_fname + time_str

    # create a folder for the current testing session in the "results" folder
    session_folder = os.path.join(participant_folder, session_identifier)
    if not os.path.exists(session_folder):
        os.makedirs(session_folder)

    # Step 1: Connect to the EyeLink Host PC
    #
    # The Host IP address, by default, is "100.1.1.1".
    # the "el_tracker" objected created here can be accessed through the Pylink
    # Set the Host PC address to "None" (without quotes) to run the script
    # in "Dummy Mode"
    if dummy_mode:
        el_tracker = pylink.EyeLink(None)
    else:
        try:
            el_tracker = pylink.EyeLink("100.1.1.1")
        except RuntimeError as error:
            print('ERROR:', error)
            pygame.quit()
            sys.exit()

    # Step 2: Open an EDF data file on the Host PC
    edf_file = edf_fname + ".EDF"
    current_edf_file = edf_file
    try:
        el_tracker.openDataFile(edf_file)
    except RuntimeError as err:
        print('ERROR:', err)
        # close the link if we have one open
        if el_tracker.isConnected():
            el_tracker.close()
        pygame.quit()
        sys.exit()

    # Add a header text to the EDF file to identify the current experiment name
    # This is OPTIONAL. If your text starts with "RECORDED BY " it will be
    # available in DataViewer's Inspector window by clicking
    # the EDF session node in the top panel and looking for the "Recorded By:"
    # field in the bottom panel of the Inspector.
    preamble_text = 'RECORDED BY %s' % os.path.basename(__file__)
    el_tracker.sendCommand("add_file_preamble_text '%s'" % preamble_text)

    # Step 3: Configure the tracker
    #
    # Put the tracker in offline mode before we change tracking parameters
    el_tracker.setOfflineMode()

    # Get the software version:  1-EyeLink I, 2-EyeLink II, 3/4-EyeLink 1000,
    # 5-EyeLink 1000 Plus, 6-Portable DUO
    eyelink_ver = 0  # set version to 0, in case running in Dummy mode
    if not dummy_mode:
        vstr = el_tracker.getTrackerVersionString()
        eyelink_ver = int(vstr.split()[-1].split('.')[0])
        # print out some version info in the shell
        print('Running experiment on %s, version %d' % (vstr, eyelink_ver))

    # File and Link data control
    # what eye events to save in the EDF file, include everything by default
    file_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON,INPUT'
    # what eye events to make available over the link, include everything by default
    link_event_flags = 'LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON,FIXUPDATE,INPUT'
    # what sample data to save in the EDF data file and to make available
    # over the link, include the 'HTARGET' flag to save head target sticker
    # data for supported eye trackers
    if eyelink_ver > 3:
        file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,HTARGET,GAZERES,BUTTON,STATUS,INPUT'
        link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,HTARGET,STATUS,INPUT'
    else:
        file_sample_flags = 'LEFT,RIGHT,GAZE,HREF,RAW,AREA,GAZERES,BUTTON,STATUS,INPUT'
        link_sample_flags = 'LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS,INPUT'
    el_tracker.sendCommand("file_event_filter = %s" % file_event_flags)
    el_tracker.sendCommand("file_sample_data = %s" % file_sample_flags)
    el_tracker.sendCommand("link_event_filter = %s" % link_event_flags)
    el_tracker.sendCommand("link_sample_data = %s" % link_sample_flags)

    # Optional tracking parameters
    # Sample rate, 250, 500, 1000, or 2000, check your tracker specification
    # if eyelink_ver > 2:
    #     el_tracker.sendCommand("sample_rate 1000")
    # Choose a calibration type, H3, HV3, HV5, HV13 (HV = horizontal/vertical),
    el_tracker.sendCommand("calibration_type = HV9")
    # Set a gamepad button to accept calibration/drift check target
    # You need a supported gamepad/button box that is connected to the Host PC
    el_tracker.sendCommand("button_function 5 'accept_target_fixation'")
    el_tracker.setScreenSimulationDistance(850)
    # Step 4: set up a graphics environment for calibration
        
    # scn_width, scn_height = win.get_size()
    pygame.mouse.set_visible(False)  # hide mouse cursor

    # Pass the display pixel coordinates (left, top, right, bottom) to the tracker
    # see the EyeLink Installation Guide, "Customizing Screen Settings"
    el_coords = "screen_pixel_coords = 0 0 %d %d" % (scn_width - 1, scn_height - 1)
    el_tracker.sendCommand(el_coords)
    # el_tracker.sendCommand("binocular_enabled = YES")
    el_tracker.sendCommand("driftcorrect_cr_disable = OFF")
    # el_tracker.sendCommand("online_dcorr_refposn 1920,1080")
    # el_tracker.sendCommand("online_dcorr_button = ON")
    # el_tracker.sendCommand("key_function F9 'online_dcorr_trigger'")

    # Write a DISPLAY_COORDS message to the EDF file
    # Data Viewer needs this piece of info for proper visualization, see Data
    # Viewer User Manual, "Protocol for EyeLink Data to Viewer Integration"
    dv_coords = "DISPLAY_COORDS  0 0 %d %d" % (scn_width - 1, scn_height - 1)
    el_tracker.sendMessage(dv_coords)

    # Configure a graphics environment (genv) for tracker calibration
    genv = CalibrationGraphics(el_tracker, win)

    # Set background and foreground colors
    # parameters: foreground_color, background_color
    foreground_color = (0, 0, 0)
    background_color = (128, 128, 128)
    genv.setCalibrationColors(foreground_color, background_color)

    # Set up the calibration target
    # Use the default calibration target
    genv.setTargetType('circle')

    # Configure the size of the calibration target (in pixels)
    genv.setTargetSize(24)


    genv.setCalibrationSounds('EyeTracking\\type.wav', 'EyeTracking\\qbeep.wav', 'EyeTracking\\error.wav')

    # Request Pylink to use the Pygame window we opened above for calibration
    pylink.openGraphicsEx(genv)
    pygame.mouse.set_visible(False)  # hide mouse cursor


    try:
        el_tracker.doTrackerSetup()
    except RuntimeError as err:
        print('ERROR:', err)
        el_tracker.exitCalibration()
        
    # if not dummy_mode:
    #     pylink.pumpDelay(100)  # wait for the tracker to settle
    #     pylink.setDriftCorrectSounds("off")

    
    pygame.mouse.set_visible(True)  # hide mouse cursor

    return el_tracker, edf_fname


# def show_message(message, fg_color, bg_color):
#     """ show messages on the screen

#     message: The message you would like to show on the screen
#     fg_color/bg_color: color for the texts and the background screen
#     """

#     # clear the screen and blit the texts
#     win_surf = win
#     win_surf.fill(bg_color)

#     scn_w, scn_h = win_surf.get_size()
#     message_fnt = pygame.font.SysFont('Arial', 32)
#     msgs = message.split('\n')
#     for i in range(len(msgs)):
#         message_surf = message_fnt.render(msgs[i], True, fg_color)
#         w, h = message_surf.get_size()
#         msg_y = scn_h / 2 + h / 2 * 2.5 * (i - len(msgs) / 2.0)
#         win_surf.blit(message_surf, (int(scn_w / 2 - w / 2), int(msg_y)))

#     pygame.display.flip()


# def wait_key(key_list, duration=sys.maxsize):
#     """ detect and return a keypress, terminate the task if ESCAPE is pressed

#     parameters:
#     key_list: allowable keys (pygame key constants, e.g., [K_a, K_ESCAPE]
#     duration: the maximum time allowed to issue a response (in ms)
#               wait for response 'indefinitely' (with sys.maxsize)
#     """

#     got_key = False
#     # clear all cached events if there are any
#     pygame.event.clear()
#     t_start = pygame.time.get_ticks()
#     resp = [None, t_start, -1]

#     while not got_key:
#         # check for time out
#         if (pygame.time.get_ticks() - t_start) > duration:
#             break

#         # check key presses
#         for ev in pygame.event.get():
#             if ev.type == KEYDOWN:
#                 if ev.key in key_list:
#                     resp = [pygame.key.name(ev.key),
#                             t_start,
#                             pygame.time.get_ticks()]
#                     got_key = True

#             if (ev.type == KEYDOWN) and (ev.key == K_c):
#                 if ev.mod in [KMOD_LCTRL, KMOD_RCTRL, 4160, 4224]:
#                     terminate_task()

#     # clear the screen following each keyboard response
#     win_surf = win
#     win_surf.fill(genv.getBackgroundColor())
#     pygame.display.flip()

#     return resp


def terminate_task(task_name, performance):
    """ Terminate the task gracefully and retrieve the EDF data file

    file_to_retrieve: The EDF on the Host that we would like to download
    win: the current window used by the experimental script
    """

    # disconnect from the tracker if there is an active connection
    el_tracker = pylink.getEYELINK()

    if el_tracker.isConnected():
        # Terminate the current trial first if the task terminated prematurely
        error = el_tracker.isRecording()
        if error == pylink.TRIAL_OK:
            # abort_trial()
            print("Aborting trial due to task termination")
        # Put tracker in Offline mode
        el_tracker.setOfflineMode()

        # Clear the Host PC screen and wait for 500 ms
        el_tracker.sendCommand('clear_screen 0')
        pylink.msecDelay(500)

        # Close the edf data file on the Host
        el_tracker.closeDataFile()

        # Download the EDF data file from the Host PC to a local data folder
        # parameters: source_file_on_the_host, destination_file_on_local_drive
        local_edf = os.path.join(session_folder, task_name+'_'+ participant_name + '.EDF')
        try:
            el_tracker.receiveDataFile(current_edf_file, local_edf)
        except RuntimeError as error:
            print('ERROR:', error)
        # Save performance data

        performance_file = os.path.join(session_folder, f"{task_name}_{participant_name}_performance.json")
        try:
            with open(performance_file, 'w') as f:
                json.dump(performance, f, indent=2)
        except Exception as e:
            print("Failed to save performance data:", e)
        # el_tracker.close()

    pylink.closeGraphics()


# def abort_trial():
#     """Ends recording

#     We add 100 msec to catch final events
#     """

#     # get the currently active tracker object (connection)
#     el_tracker = pylink.getEYELINK()

#     # Stop recording
#     if el_tracker.isRecording():
#         # add 100 ms to catch final trial events
#         pylink.pumpDelay(100)
#         el_tracker.stopRecording()

#     # Send a message to clear the Data Viewer screen
#     el_tracker.sendMessage('!V CLEAR 128 128 128')

#     # send a message to mark trial end
#     el_tracker.sendMessage('TRIAL_RESULT %d' % pylink.TRIAL_ERROR)

#     return pylink.TRIAL_ERROR


# def run_trial(trial_pars, trial_index):
#     """ Helper function specifying the events that will occur in a single trial

#     trial_pars - a list containing trial parameters, e.g.,
#                 ['cond_1', 'img_1.jpg']
#     trial_index - record the order of trial presentation in the task
#     """

#     # unpacking the trial parameters
#     cond, pic = trial_pars

#     # load the image to display, here we stretch the image to fill full screen
#     img = pygame.image.load('./images/' + pic)
#     img = pygame.transform.scale(img, (scn_width, scn_height))

#     # get the currently active window
#     surf = win

#     # get a reference to the currently active EyeLink connection
#     el_tracker = pylink.getEYELINK()

#     # put the tracker in the offline mode first
#     el_tracker.setOfflineMode()

#     # clear the host screen before we draw the backdrop
#     el_tracker.sendCommand('clear_screen 0')

#     # show a backdrop image on the Host screen, imageBackdrop() the recommended
#     # function, if you do not need to scale the image on the Host
#     # parameters: image_file, crop_x, crop_y, crop_width, crop_height,
#     #             x, y on the Host, drawing options
# ##    el_tracker.imageBackdrop(os.path.join('images', pic),
# ##                             0, 0, scn_width, scn_height, 0, 0,
# ##                             pylink.BX_MAXCONTRAST)

#     # If you need to scale the backdrop image on the Host, use the old Pylink
#     # bitmapBackdrop(), which requires an additional step of converting the
#     # image pixels into a recognizable format by the Host PC.
#     # pixels = [line1, ...lineH], line = [pix1,...pixW], pix=(R,G,B)
#     #
#     # the bitmapBackdrop() command takes time to return, not recommended
#     # for tasks where the ITI matters, e.g., in an event-related fMRI task
#     # parameters: width, height, pixel, crop_x, crop_y,
#     #             crop_width, crop_height, x, y on the Host, drawing options
#     #
#     # Use the code commented below to convert the image and send the backdrop
#     #
#     pixels = [[img.get_at((i, j))[0:3] for i in range(scn_width)]
#               for j in range(scn_height)]
#     el_tracker.bitmapBackdrop(scn_width, scn_height, pixels,
#                               0, 0, scn_width, scn_height,
#                               0, 0, pylink.BX_MAXCONTRAST)

#     # OPTIONAL: draw landmarks on the Host screen
#     # In addition to backdrop image, You may draw simples on the Host PC to use
#     # as landmarks. For illustration purpose, here we draw some texts and a box
#     # For a list of supported draw commands, see the "COMMANDS.INI" file on the
#     # Host PC (under /elcl/exe)
#     left = int(scn_width/2.0) - 60
#     top = int(scn_height/2.0) - 60
#     right = int(scn_width/2.0) + 60
#     bottom = int(scn_height/2.0) + 60
#     draw_cmd = 'draw_filled_box %d %d %d %d 1' % (left, top, right, bottom)
#     el_tracker.sendCommand(draw_cmd)

#     # send a "TRIALID" message to mark the start of a trial, see Data
#     # Viewer User Manual, "Protocol for EyeLink Data to Viewer Integration"
#     el_tracker.sendMessage('TRIALID %d' % trial_index)

#     # record_status_message : show some info on the Host PC
#     # here we show how many trial has been tested
#     status_msg = 'TRIAL number %d' % trial_index
#     el_tracker.sendCommand("record_status_message '%s'" % status_msg)

#     # drift check
#     # we recommend drift-check at the beginning of each trial
#     # the doDriftCorrect() function requires target position in integers
#     # the last two arguments:
#     # draw_target (1-default, 0-draw the target then call doDriftCorrect)
#     # allow_setup (1-press ESCAPE to recalibrate, 0-not allowed)
#     #
#     # Skip drift-check if running the script in Dummy Mode
#     while not dummy_mode:
#         # terminate the task if no longer connected to the tracker or
#         # user pressed Ctrl-C to terminate the task
#         if (not el_tracker.isConnected()) or el_tracker.breakPressed():
#             terminate_task()
#             return pylink.ABORT_EXPT

#         # drift-check and re-do camera setup if ESCAPE is pressed
#         try:
#             error = el_tracker.doDriftCorrect(int(scn_width/2.0),
#                                               int(scn_height/2.0), 1, 1)
#             # break following a success drift-check
#             if error is not pylink.ESC_KEY:
#                 break
#         except:
#             pass

#     # put tracker in idle/offline mode before recording
#     el_tracker.setOfflineMode()

#     # Start recording
#     # arguments: sample_to_file, events_to_file, sample_over_link,
#     # event_over_link (1-yes, 0-no)
#     try:
#         el_tracker.startRecording(1, 1, 1, 1)
#     except RuntimeError as error:
#         print("ERROR:", error)
#         abort_trial()
#         return pylink.TRIAL_ERROR

#     # Allocate some time for the tracker to cache some samples
#     pylink.pumpDelay(100)

#     # show the image
#     surf.fill((128, 128, 128))  # clear the screen
#     surf.blit(img, (0, 0))
#     pygame.display.flip()
#     onset_time = pygame.time.get_ticks()  # image onset time

#     # send over a message to mark the onset of the image
#     el_tracker.sendMessage('image_onset')

#     # Send a message to clear the Data Viewer screen, get it ready for
#     # drawing the pictures during visualization
#     el_tracker.sendMessage('!V CLEAR 128 128 128')

#     # send over a message to specify where the image is stored relative
#     # to the EDF data file, see Data Viewer User Manual, "Protocol for
#     # EyeLink Data to Viewer Integration"
#     bg_image = '../../images/' + pic
#     imgload_msg = '!V IMGLOAD CENTER %s %d %d %d %d' % (bg_image,
#                                                         int(scn_width/2.0),
#                                                         int(scn_height/2.0),
#                                                         int(scn_width),
#                                                         int(scn_height))
#     el_tracker.sendMessage(imgload_msg)

#     # send interest area messages to record in the EDF data file
#     # here we draw a rectangular IA, for illustration purposes
#     # format: !V IAREA RECTANGLE <id> <left> <top> <right> <bottom> [label]
#     # for all supported interest area commands, see the Data Viewer Manual,
#     # "Protocol for EyeLink Data to Viewer Integration"
#     ia_pars = (1, left, top, right, bottom, 'screen_center')
#     el_tracker.sendMessage('!V IAREA RECTANGLE %d %d %d %d %d %s' % ia_pars)

#     # show the image for 5 secs; break if the SPACEBAR is pressed
#     pygame.event.clear()  # clear all cached events if there were any
#     get_keypress = False
#     RT = -1
#     while not get_keypress:
#         # present the picture for a maximum of 5 seconds
#         if pygame.time.get_ticks() - onset_time >= 5000:
#             el_tracker.sendMessage('time_out')
#             break

#         # abort the current trial if the tracker is no longer recording
#         error = el_tracker.isRecording()
#         if error is not pylink.TRIAL_OK:
#             el_tracker.sendMessage('tracker_disconnected')
#             abort_trial()
#             return error

#         # check for keyboard events
#         for ev in pygame.event.get():
#             # Stop stimulus presentation when the spacebar is pressed
#             if (ev.type == KEYDOWN) and (ev.key == K_SPACE):
#                 # send over a message to log the key press
#                 el_tracker.sendMessage('key_pressed')

#                 # get response time in ms, PsychoPy report time in sec
#                 RT = pygame.time.get_ticks() - onset_time
#                 get_keypress = True

#             # Abort a trial if "ESCAPE" is pressed
#             if (ev.type == KEYDOWN) and (ev.key == K_ESCAPE):
#                 el_tracker.sendMessage('trial_skipped_by_user')
#                 # clear the screen
#                 surf.fill((128, 128, 128))
#                 pygame.display.flip()
#                 # abort trial
#                 abort_trial()
#                 return pylink.SKIP_TRIAL

#             # Terminate the task if Ctrl-c
#             if (ev.type == KEYDOWN) and (ev.key == K_c):
#                 if ev.mod in [KMOD_LCTRL, KMOD_RCTRL, 4160, 4224]:
#                     el_tracker.sendMessage('terminated_by_user')
#                     terminate_task()
#                     return pylink.ABORT_EXPT

#     # clear the screen
#     surf.fill((128, 128, 128))
#     pygame.display.flip()
#     el_tracker.sendMessage('blank_screen')
#     # send a message to clear the Data Viewer screen as well
#     el_tracker.sendMessage('!V CLEAR 128 128 128')

#     # stop recording; add 100 msec to catch final events before stopping
#     pylink.pumpDelay(100)
#     el_tracker.stopRecording()

#     # record trial variables to the EDF data file, for details, see Data
#     # Viewer User Manual, "Protocol for EyeLink Data to Viewer Integration"
#     el_tracker.sendMessage('!V TRIAL_VAR condition %s' % cond)
#     el_tracker.sendMessage('!V TRIAL_VAR image %s' % pic)
#     el_tracker.sendMessage('!V TRIAL_VAR RT %d' % RT)

#     # send a 'TRIAL_RESULT' message to mark the end of trial, see Data
#     # Viewer User Manual, "Protocol for EyeLink Data to Viewer Integration"
#     el_tracker.sendMessage('TRIAL_RESULT %d' % pylink.TRIAL_OK)


# # Step 5: Set up the camera and calibrate the tracker

# # Show the task instructions
# task_msg = 'In the task, you may press the SPACEBAR to end a trial\n' + \
#     '\nPress Ctrl-C to if you need to quit the task early\n'
# if dummy_mode:
#     task_msg = task_msg + '\nNow, press ENTER to start the task'
# else:
#     task_msg = task_msg + '\nNow, press ENTER to calibrate tracker'

# # Pygame bug warning
# pygame_warning = '\n\nDue to a bug in Pygame 2, the window may have lost' + \
#                  '\nfocus and stopped accepting keyboard inputs.' + \
#                  '\nClicking the mouse helps get around this issue.'
# if pygame.__version__.split('.')[0] == '2':
#     task_msg = task_msg + pygame_warning

# show_message(task_msg, (0, 0, 0), (128, 128, 128))
# wait_key([K_RETURN])

# # skip this step if running the script in Dummy Mode
# if not dummy_mode:
#     try:
#         el_tracker.doTrackerSetup()
#     except RuntimeError as err:
#         print('ERROR:', err)
#         el_tracker.exitCalibration()

# # Step 6: Run the experimental trials, index all the trials

# # construct a list of 4 trials
# test_list = trials[:]*2

# # randomize the trial list
# random.shuffle(test_list)

# trial_index = 1
# for trial_pars in test_list:
#     run_trial(trial_pars, trial_index)
#     trial_index += 1

# # Step 7: disconnect, download the EDF file, then terminate the task
# terminate_task()
