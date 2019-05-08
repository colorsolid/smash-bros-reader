import json
import os
from   pynput import keyboard
from   queue import Empty
import re
import smash_game
import smash_utility as ut
import threading
import time


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
            (),
            ('FINAL', 'ID')
        ]

        self.reset()


    def reset(self):
        self.current_type_index = 0
        self.list_limit = 3
        self.sim_list = [0] * self.list_limit
        self.cont = True
        self.current_game_num = len(ut.load_game_data()) + 1
        self.game = smash_game.Game(self.current_game_num)
        self.timer_detected = False
        self.timer_visible = False
        self.timer_running = False
        self.timer_running_templates = (None, None)
        self.timer_sim_hits = 0


    def run(self):
        _print('Watching for flags')
        self.gui_queue.put({'status': 'Watching for flag screen'})
        while self.cont:
            self.cap = ut.capture_screen()
            if self.current_type_index >= 2:
                timer_vis_sim = self.check_timer_visibility()
                timer_milli_sim = 0
                if self.timer_detected:
                    timer_milli_sim = self.check_timer_movement()
            if self.current_type_index == 1:
                players = [player for team in self.game.teams for player in team.players]
                names = {player.character_name for player in players}
                if len(names) < len(players) and not self.game.team_mode:
                    _print('GAME CANCELLED DUE TO DUPLICATE CHARACTER IN FFA')
                    self.game.cancelled = True
                    # self.current_type_index = 5
                    # self.read_screen_data()
                if '...' in names:
                    _print('GAME CANCELLED DUE TO UNREADABLE CHARACTER NAME')
            if self.current_type_index == 2:
                if self.timer_detected:
                    _print(f'timer detected: {timer_vis_sim}')
                    self.read_screen_data()
            elif self.current_type_index == 3:
                if self.timer_running:
                    _print(f'timer movemement detected: {timer_milli_sim}')
                    self.read_screen_data()
            elif self.current_type_index == 4:
                self.read_screen_data()
            else:
                self.check_screen_basic()
            self.check_queue()
            time.sleep(0.01)


    def check_queue(self):
        if self.queue:
            try:
                item = self.queue.get(block=False)
                if item == 'quit':
                    self.cont = False
            except Empty:
                pass


    # @ut.pad_time(0.20)
    def check_screen_basic(self):
        screen, area = self.id_coords[self.current_type_index]
        coords = ut.COORDS[screen][area]
        if (screen, area) == ('FINAL', 'ID'):
            if self.game.team_mode:
                coords = coords[1]
            else:
                coords = coords[0]
        crop = self.cap.crop(coords)
        template = ut.TEMPLATES[screen][area]
        self.sim = ut.avg_sim(crop, template)
        self.sim_list.insert(0, self.sim)
        del self.sim_list[-1]
        avg = sum(self.sim_list) / len(self.sim_list)
        if avg > 90:
            _print(f'Screen type sim: {avg}')
            self.read_screen_data()
            self.sim_list = [0] * self.list_limit


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


    def read_screen_data(self):
        if self.current_type_index == 0:
            self.game = smash_game.Game(self.current_game_num)
            self.gui_queue.put('update')
            _print('Flags detected')
            self.gui_queue.put({'status': 'Watching for card screen'})
        if self.current_type_index == 1:
            _print('Flags cards')
            self.gui_queue.put({'status': 'Reading cards'})
            self.game.read_card_screen(self.cap)
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for battle pregame'})
        if self.current_type_index == 2:
            _print('Battle pregame detected')
            self.game.read_start_screen(self.cap)
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for battle start'})
        if self.current_type_index == 3:
            _print('Battle started')
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for battle end'})
        if self.current_type_index == 4:
            _print('Battle end detected')
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for battle results'})
        if self.current_type_index == 5:
            _print('Battle results detected')
            self.game.read_results_screen(self.cap)
            self.gui_queue.put('update')
            self.gui_queue.put({'status': 'Watching for flag screen'})
            ut.save_game_data(self.game.serialize())
        self.current_type_index += 1
        if self.current_type_index >= 6:
            self.current_type_index = 0
        _print(f'Mode changed to {self.current_type_index}')
        # _print(json.dumps(self.game.serialize(), separators=(',', ': ')))


class KeyThread(threading.Thread):
    def __init__(self, callback, *args, **kwargs):
        super().__init__()

        self.callback = callback

        self.key = keyboard.KeyCode(char='g')


    def run(self):
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()


    def on_press(self, key):
        if key == self.key:
            self.callback()
