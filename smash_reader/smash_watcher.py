import json
from   logger import log_exception
import os
from   queue import Empty
import re
import requests
import smash_game
import smash_utility as ut
import sys
import threading
import time

sys.excepthook = log_exception


output = True
def _print(*args, **kwargs):
    if output:
        args = list(args)
        args.insert(0, '<Watcher>')
        print(*args, **kwargs)


class Watcher(threading.Thread):
    def __init__(self, watcher_queue, gui_queue):
        # print('\n')
        super().__init__()
        self.queue = watcher_queue
        self.gui_queue = gui_queue
        self.id_coords = [
            ('LOBBY', 'FLAGS_ID'),
            ('LOBBY', 'CARDS_ID'),
            (),
            (),
            ('GAME', 'END_ID'),
            ('FINAL', 'ID'),
            ('FINAL', 'ID2')
        ]

        self.locked = False

        self.reset()


    # Game finished or cancelled
    def reset(self):
        if not self.locked:
            self.current_type_index = 0
        self.list_limit = 3
        self.sim_lists = [[0] * self.list_limit for _ in range(len(self.id_coords))]
        self.cont = True
        self.current_game_num = len(ut.load_game_data()) + 1
        self.game = smash_game.Game(self.current_game_num)
        self.timer_detected = False
        self.timer_visible = False
        self.timer_running = False
        self.timer_running_templates = (None, None)
        self.timer_sim_hits = 0


    # Starts when watcher is created and loops forever
    def run(self):
        _print('Watching for flags')
        self.gui_queue.put({'status': 'Watching for flag screen'})
        while self.cont:
            timer_vis_sim = 0
            timer_milli_sim = 0
            if self.game.cancelled:
                self.reset()
                if not self.locked:
                    self.gui_queue.put('update')
                    self.gui_queue.put({'status': 'Watching for flag screen'})
            self.cap = ut.capture_screen()
            # check timer visibility and movement, set class variables
            if self.current_type_index >= 2:
                timer_vis_sim = self.check_timer_visibility()
                timer_milli_sim = 0
                if self.timer_detected:
                    timer_milli_sim = self.check_timer_movement()
            # look for the timer at the beginning
            if self.current_type_index == 2:
                if self.timer_detected:
                    _print(f'timer detected: {timer_vis_sim}')
                    self.read_screen_data()
            # wait for the timer to start moving
            elif self.current_type_index == 3:
                if self.timer_running:
                    _print(f'timer movemement detected: {timer_milli_sim}')
                    self.read_screen_data()
            # check to see if the timer is stopped, or the "GAME" text is
            # detected, or the results screen is detected
            elif self.current_type_index == 4:
                if self.check_screen_basic() > 90:
                    # pass because read_screen_data will be called if True
                    # and the rest of the checks will be skipped
                    pass
                else:
                    # Timer stopped
                    if not self.timer_running:
                        self.read_screen_data()
                    # Results screen detected
                    else:
                        checks = [
                            self.check_screen_basic(index=5, normal=False),
                            self.check_screen_basic(index=6, normal=False)
                        ]
                        if sum(checks) / 2 > 80:
                            # run twice because the match end screen was missed
                            self.read_screen_data()
                            self.read_screen_data()
            # check for current basic template (flags, cards, results)
            else:
                self.check_screen_basic()
            self.check_queue()
            time.sleep(0.1)


    def check_queue(self):
        if self.queue:
            try:
                item = self.queue.get(block=False)
                if item == 'quit':
                    self.cont = False
            except Empty:
                pass


    def lock(self, index):
        print('lock')
        self.current_type_index = index - 1
        self.read_screen_data()
        self.locked = True


    def unlock(self):
        self.locked = False
        self.reset()


    # @ut.pad_time(0.20)
    def check_screen_basic(self, index=-1, normal=True, screen=None, area=None):
        if index == -1:
            index = self.current_type_index
        if not screen and not area:
            screen, area = self.id_coords[index]
        sim = ut.area_sim(self.cap, screen, area)

        l = self.sim_lists[index]
        l.insert(0, sim)
        del l[-1]

        avg = sum(l) / len(l)
        if avg > 90:
            _print(f'Screen type {{{index}}} sim: {avg}')
            if normal:
                l = [0] * self.list_limit
                self.read_screen_data()
        return avg


    def check_timer_visibility(self):
        timer_vis_crop = self.cap.crop(ut.COORDS['GAME']['TIMER_VISIBLE'])
        template = ut.TEMPLATES['GAME']['TIMER_VISIBLE']
        timer_vis_sim = ut.avg_sim(timer_vis_crop, template)
        if timer_vis_sim > 95:
            # _print(f'timer vis sim: {timer_vis_sim}')
            if not self.timer_detected:
                self.timer_detected = True
            self.timer_visible = True
        else:
            self.timer_visible = False
        return timer_vis_sim


    def check_timer_movement(self):
        timer_sim = 0
        if self.timer_visible:
            coords = ut.COORDS['GAME']['TIMER_MILLI']
            crops = [self.cap.crop(coord) for coord in coords]
            # [crop.show() for crop in crops]
            if all(self.timer_running_templates):
                timer_sim = sum([ut.avg_sim(t, c) for t, c in zip(self.timer_running_templates, crops)]) / 2
                # for i, crop in enumerate(crops):
                #     timer_sim = ut.avg_sim(crop, self.timer_running_templates[i])  / (i + 1)
                if timer_sim > 90:
                    _print(f'timer sim: {timer_sim}')
                    self.timer_sim_hits += 1
                    if self.timer_sim_hits >= 3:
                        if self.timer_running:
                            # self.read_screen_data()
                            self.timer_running = False
                else:
                    self.timer_running = True
                    self.timer_sim_hits = 0
            self.timer_running_templates = crops
        return timer_sim


    def battle_watcher(self):
        pass


    def filter_and_post(self, game):
        data = {
            'game': ut.filter_game_data(
                game,
                self.current_type_index
            ),
            'mode': self.current_type_index
        }
        ut.post_data(data)


    def read_screen_data(self):
        # Flags
        if self.current_type_index == 0:
            self.gui_queue.put('update')
            _print('Flags detected')
            self.gui_queue.put({'status': 'Watching for card screen'})
        # Cards
        if self.current_type_index == 1:
            _print('Cards detected')
            self.gui_queue.put({'status': 'Reading cards'})
            time.sleep(1)
            self.cap = ut.capture_screen()
            self.game.read_card_screen(self.cap)
            self.filter_and_post(self.game.serialize(images_bool=False))
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for battle pregame'})
        # Pregame
        if self.current_type_index == 2:
            _print('Battle pregame detected')
            self.game.read_start_screen(self.cap)
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for battle start'})
        # Game started
        if self.current_type_index == 3:
            _print('Battle start detected')
            self.filter_and_post(self.game.serialize(images_bool=False))
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for battle end'})
        # Game ended
        if self.current_type_index == 4:
            _print('Battle end detected')
            self.filter_and_post(self.game.serialize(images_bool=False))
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for battle results'})
        # Results
        if self.current_type_index == 5:
            _print('Battle results detected')
            self.game.read_results_screen(self.cap)
            self.filter_and_post(self.game.serialize(images_bool=False))
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for flag screen'})
            # ut.save_game_data(self.game.serialize())
        if not self.locked:
            self.current_type_index += 1
            if self.current_type_index >= 6:
                self.reset()
            _print(f'Mode changed to {self.current_type_index}')
        # _print(json.dumps(self.game.serialize(), separators=(',', ': ')))
