# import cv2
# from   datetime import datetime
# import imutils
# import numpy as np
import os
from   PIL import ImageGrab, Image, ImageDraw
# import pytesseract as pyt
# from   queue import Queue, Empty
import re
import smash_utility as ut
# import sys
# import threading
# import time


COORDS = {
    'IDS': {
        'LOBBY_BASIC': (145, 32, 321, 70),
        'LOBBY_CARDS': (671, 152, 1247, 188),
        'LOBBY_FLAGS': (394, 291, 1525, 433),
        'FIGHT_START': (1722, 61, 1798, 89),
        'TIMES_UP': (465, 299, 1451, 409),
        'SUDDEN_DEATH': (340, 172, 1602, 345),
        'FIGHT_END': (411, 462, 1481, 522),
        'FIGHT_RESULTS_SOLO': (468, 49, 550, 296),
        'FIGHT_RESULTS_TEAM': (204, 388, 286, 635)
    }
}


BASE_DIR = os.path.realpath(os.path.dirname(__file__))
CAPTURES_DIR = os.path.join(BASE_DIR, 'captures')
if not os.path.isdir(CAPTURES_DIR):
    os.mkdir(CAPTURES_DIR)
TEMPLATES = {}


for root, dirs, files in os.walk(os.path.join(BASE_DIR, 'templates'), topdown=False):
    for file in files:
        path = os.path.join(root, file)
        name = os.path.splitext(file)[0]
        type = os.path.split(root)[1].upper()
        if type in TEMPLATES:
            TEMPLATES[type][name] = Image.open(path)
        else:
            TEMPLATES[type] = {name: Image.open(path)}


class Watcher:
    def __init__(self):
        self.coord_types = [
            'LOBBY_FLAGS',
            'LOBBY_CARDS',
            'FIGHT_START',
            'FIGHT_END',
            ('FIGHT_RESULTS_SOLO', 'FIGHT_RESULTS_TEAM')
        ]

        self.current_type_index = 0
        self.captures = os.listdir(CAPTURES_DIR)
        ssplit = lambda s: int(re.match('\d+', s).group())
        game_nums = list({ssplit(file) for file in self.captures})
        game_nums.sort()
        if game_nums:
            self.current_game_num = game_nums[-1] + 1
        else:
            self.current_game_num = 1
        self.main()


    def main(self):
        list_limit = 3
        sim_list = [0] * list_limit
        while True:
            sim, area_name, cap = self.watch_screen()
            if sim:
                sim_list.insert(0, sim)
                del sim_list[-1]
                avg = sum(sim_list) / len(sim_list)
                if avg > 80:
                    filename = '{}.{}.{}.png'.format(
                        str(self.current_game_num).rjust(4, '0'),
                        self.current_type_index + 1,
                        area_name
                    )
                    filepath = os.path.join(CAPTURES_DIR, filename)
                    try:
                        cap.save(filepath)
                        print(f'saved: {filename}')
                    except:
                        print('Unable to save image')
                    sim_list = [0] * list_limit
                    self.current_type_index += 1
                    if self.current_type_index >= len(self.coord_types):
                        self.current_type_index = 0
                        self.current_game_num += 1


    @ut.pad_time(0.20)
    def watch_screen(self):
        coord_type = self.coord_types[self.current_type_index]
        if not isinstance(coord_type, (list, tuple)):
            coord_type = [coord_type]
        cap = ut.capture_screen()
        sims = []
        for coord_area_name in coord_type:
            template = TEMPLATES['IDS'][coord_area_name]
            coords = COORDS['IDS'][coord_area_name]
            crop = cap.crop(coords)
            sim = ut.avg_sim(crop, template)
            sims.append((sim, coord_area_name, cap))
        sims.sort(key=lambda item: item[0])
        return sims[-1]



# Scan frame and return type with highest similarity
def check_frame_type(path, save=False):
    comp_funcs = [ut.compare_chops, ut.compare_skim]
    img = Image.open(path)
    highest_sim = {'name': '', 'val': 0}
    for id_name in COORDS['IDS']:
        coord = COORDS['IDS'][id_name]
        crop = img.crop(coord)
        if save:
            crop.save(f'{id_name}.png')
        for template_name in TEMPLATES['IDS']:
            template = TEMPLATES['IDS'][template_name]
            sims = [comp(crop, template) for comp in comp_funcs]
            avg = sum(sims) / len(sims)
            if avg > highest_sim['val']:
                highest_sim['val'] = avg
                highest_sim['name'] = id_name
    print(f'{os.path.split(path)[1]} matches {highest_sim["name"]} with a sim_score of {highest_sim["val"]}')
    return highest_sim['name']


@ut.time_this
def read_numbers(img):
    return pyt.image_to_string(img, config='outputbase digits')


@ut.time_this
def screens_folder_test():
    screens = [os.path.join(BASE_DIR, 'screens', f) for f in os.listdir(os.path.join(BASE_DIR, 'screens'))]
    screens = [s for s in screens if os.path.isfile(s)]
    screens.sort(key=lambda path: int(os.path.split(path)[1].split('.')[0]))
    for screen in screens:
        check_frame_type(screen)
    #check_frame_type(screens[30], True)


# flags → cards → start → end → results ⮌


if __name__ == '__main__':
    watcher = Watcher()
    # screens_folder_test()
