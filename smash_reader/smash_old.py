# import cv2
# from   datetime import datetime
# import imutils
import json
# import numpy as np
import os
from   PIL import ImageGrab, Image, ImageDraw
# import pytesseract as pyt
from   queue import Queue
import random
import re
import smash_game
import smash_utility as ut
import smash_watcher
import sys
import threading
# import time


BASE_DIR = os.path.realpath(os.path.dirname(__file__))
CAPTURES_DIR = os.path.join(BASE_DIR, 'captures')
if not os.path.isdir(CAPTURES_DIR):
    os.mkdir(CAPTURES_DIR)


# Scan frame and return type with highest similarity
def check_frame_type(path, save=False):
    comp_funcs = [ut.compare_chops, ut.compare_skim]
    img = Image.open(path)
    highest_sim = {'name': '', 'val': 0}
    for id_name in ut.COORDS['IDS']:
        coord = ut.COORDS['IDS'][id_name]
        crop = img.crop(coord)
        if save:
            crop.save(f'{id_name}.png')
        for template_name in TEMPLATES['IDS']:
            template = ut.TEMPLATES['IDS'][template_name]
            sims = [comp(crop, template) for comp in comp_funcs]
            avg = sum(sims) / len(sims)
            if avg > highest_sim['val']:
                highest_sim['val'] = avg
                highest_sim['name'] = id_name
    print(f'{os.path.split(path)[1]} matches {highest_sim["name"]} with a sim_score of {highest_sim["val"]}')
    return highest_sim['name']


@ut.time_this
def screens_folder_test():
    screens = [os.path.join(BASE_DIR, 'screens', f) for f in os.listdir(os.path.join(BASE_DIR, 'screens'))]
    screens = [s for s in screens if os.path.isfile(s)]
    screens.sort(key=lambda path: int(os.path.split(path)[1].split('.')[0]))
    for screen in screens:
        ut.check_frame_type(screen)
    #check_frame_type(screens[30], True)


# flags → cards → start → end → results ⮌


if __name__ == '__main__':
    sys.excepthook = ut.log_exception
    gui_queue = Queue()
    watcher_queue = Queue()
    # fight_tester()
    watch = True
    if watch:
        watcher = smash_watcher.Watcher(watcher_queue, gui_queue)
        watcher.start()
        watcher.join()
    # screens_folder_test()
