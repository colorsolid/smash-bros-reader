from   datetime import datetime
import json
from   logger import log_exception
import numpy as np
import os
from   PIL import Image, ImageTk
from   queue import Queue, Empty
import smash_game
import smash_utility as ut
import smash_watcher
from   sys import argv, excepthook
import time
import tkinter as tk

excepthook = log_exception


TITLE = 'SmashBet Screen Watcher'

output = True
def _print(*args, **kwargs):
    if output:
        args = list(args)
        args.insert(0, '<Utility>')
        print(*args, **kwargs)

BASE_DIR = os.path.realpath(os.path.dirname(__file__))


BG = ['#282C34', '#383D48']
FG = ['#9098A6', '#9DA5B4', '#ABB3BF', '#E06C75', '#61AFEF', '#56B6C2', '#98C379']

def config_grids(widget, rows=[], columns=[]):
    [widget.rowconfigure(i, weight=weight) for i, weight in enumerate(rows)]
    [widget.columnconfigure(i, weight=weight) for i, weight in enumerate(columns)]


class Menubar(tk.Menu):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.file_menu = tk.Menu(self, tearoff=0)
        # self.file_menu.add_command(label='Load State', command=self.load_state)
        # self.file_menu.add_command(label='Save State', command=self.save_state)
        # self.file_menu.add_separator()
        self.file_menu.add_command(label='Restart', command=self.master.restart)
        self.file_menu.add_command(label='Quit', command=self.master.quit)

        self.debug_menu = tk.Menu(self, tearoff=0)
        self.debug_menu.add_command(label='Clear console', command=ut.clear_console)

        self.output_menu = tk.Menu(self, tearoff=0)
        self.output_menu.add_command(
            label='Silence watcher', command=lambda: self.toggle_output(smash_watcher, 'watcher', 0)
        )
        self.output_menu.add_command(
            label='Silence game', command=lambda: self.toggle_output(smash_game, 'game', 1)
        )
        self.output_menu.add_command(
            label='Silence utility', command=lambda: self.toggle_output(ut, 'utility', 2)
        )

        self.debug_menu.add_cascade(label='Outputs', menu=self.output_menu)
        self.debug_menu.add_separator()
        self.debug_menu.add_command(label='Print game data', command=lambda: print(self.master.game))
        self.debug_menu.add_separator()
        self.debug_menu.add_command(label='Capture cards_id template', command=ut.capture_cards_id)

        self.add_cascade(label='File', menu=self.file_menu)
        self.add_cascade(label='Debug', menu=self.debug_menu)


    def toggle_output(self, module, name, index):
        if module.output:
            self.output_menu.entryconfig(index, label=f'Unsilence {name}')
        else:
            self.output_menu.entryconfig(index, label=f'Silence {name}')
        module.output = not module.output


    def load_state(self):
        path = os.path.join(BASE_DIR, 'game_state.json')
        if os.path.isfile(path):
            with open(path, 'r') as infile:
                return json.load(infile)
        else:
            return None


    def save_state(self):
        game = self.master.game
        if game:
            path = os.path.join(BASE_DIR, 'game_state.json')
            with open(path, 'w+') as outfile:
                json.dump(game, outfile)

class PlayerFrame(tk.Frame):
    def __init__(self, master, player_info, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master

        self.info = player_info

        config_grids(self, rows=[1, 1], columns=[1, 1])

        self.player_number_label = tk.Label(self, text=f'Player {self.info["number"]}', bg=self['background'])
        self.player_number_label.grid(row=0, column=0, sticky='nsw', padx=10)

        self.character_name_label = tk.Label(
            self, text=f'Character: {self.info["character_name"].title()}', bg=self['background']
        )
        self.character_name_label.grid(row=0, column=1, sticky='nsw', padx=10)

        self.gsp_label = tk.Label(self, text=f'GSP: {self.info["gsp"]}', bg=self['background'])
        self.gsp_label.grid(row=1, column=0, sticky='nsw', padx=10)

        img = self.info['player_name_image']
        for i, row in enumerate(img):
            img[i] = [pixel * 255 for pixel in img[i]]
        arr = np.asarray(img)
        # arr = np.array(self.info['player_name_image'])
        try:
            img = Image.fromarray(arr)
            img = img.resize((200, 30), Image.NEAREST)
            # img.show()
            img = img.convert('1').tobitmap()
            bitmap = ImageTk.BitmapImage(data=img)
            self.player_name_label = tk.Label(self, image=bitmap, bg=self.master['background'])
            self.player_name_label.image = bitmap
            self.player_name_label.grid(row=1, column=1, sticky='nw', padx=10)
        except TypeError:
            _print('Image data corrupted')
            try:
                ut.dump_image_data(arr)
                _print('Image data successfully dumped')
            except:
                _print('Failed to dump image data')


class TeamFrame(tk.Frame):
    def __init__(self, master, team_info, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master

        self.info = team_info

        self.build_player_frames()


    def build_player_frames(self):
        COLORS = {
            'RED': (252, 208, 197),
            'BLUE': (163, 220, 248),
            'YELLOW': (246, 237, 166),
            'GREEN': (160, 235, 186)
        }
        if self.info['placement']:
            self.placement_label = tk.Label(
                self, bg=self['background'], fg=BG[0], text=f'{self.info["placement"]} place'
            )
        self.info['players'].sort(key=lambda player: player['number'])
        player_frames = []
        player_len = len(self.info['players'])
        self.gsp_label = tk.Label(self, bg=self['background'], fg=BG[0], text=f'Team GSP: {self.info["gsp_total"]}')
        self.gsp_label.grid(row=0, column=1, columnspan=player_len, sticky='nsw')
        config_grids(self, rows=[1]*(player_len+1), columns=[1, 1])
        config_grids(self, rows=[0])
        for i, player in enumerate(self.info['players']):
            hex_color = ut.rgb_to_hex(COLORS[self.info['color']])
            player_frames.append(PlayerFrame(self, player, bg=hex_color))
            player_frames[i].grid(row=i+1, column=0, columnspan=2, sticky='nsew', padx=10, pady=(0, 10))



class GameFrame(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master
        self.game_number = tk.StringVar()
        self.game_mode = tk.StringVar()
        self.game_map = tk.StringVar()
        self.game_duration = tk.StringVar()

        config_grids(self, rows=[0, 1], columns=[1])

        self.info_frame = tk.Frame(self, bg=BG[0])
        config_grids(self.info_frame, rows=[1, 1], columns=[1, 1])
        self.info_frame.grid(row=0, column=0, sticky='nsew')

        self.game_mode_label = tk.Label(self.info_frame, bg=BG[0], fg=FG[0], textvariable=self.game_mode)
        self.game_mode_label.grid(row=0, column=0, sticky='nsew')
        self.game_map_label = tk.Label(self.info_frame, bg=BG[0], fg=FG[0], textvariable=self.game_map)
        self.game_map_label.grid(row=0, column=1, sticky='nsew')
        self.game_number_label = tk.Label(self.info_frame, bg=BG[0], fg=FG[0], textvariable=self.game_number)
        self.game_number_label.grid(row=1, column=0, sticky='nsew')
        self.game_duration_label = tk.Label(self.info_frame, bg=BG[0], fg=FG[0], textvariable=self.game_duration)
        self.game_duration_label.grid(row=1, column=1, sticky='nsew')


    def display_info(self):
        self.master.game = self.master.watcher.game.serialize()
        game = self.master.game
        self.game_number.set(f'Game #{game["number"]}')
        self.game_map.set(f'Map: {game["map"]}')
        self.game_mode.set(f'Mode: {game["mode"]}')
        if game['duration']:
            self.game_duration.set(f'Game completed in {game["duration"]} seconds')
        elif game['start_time']:
            self.game_duration.set(
                f'Game began {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(game["start_time"]))}'
            )
        self.build_team_frames(game)


    def build_team_frames(self, game):
        color_order = ['RED', 'BLUE', 'YELLOW', 'GREEN']
        if hasattr(self, 'teams_frame'):
            self.teams_frame.destroy()
        self.teams_frame = tk.Frame(self, bg=BG[1])
        self.teams_frame.grid(row=1, column=0, sticky='nsew')
        team_len = len(game['teams'])
        config_grids(self.teams_frame, rows=[1]*team_len, columns=[1])
        game['teams'].sort(key=lambda team: color_order.index(team['color']))
        team_frames = []
        for team_index, team in enumerate(game['teams']):
            hex_color = ut.rgb_to_hex(ut.COLORS['CARDS'][team['color']])
            team_frames.append(TeamFrame(self.teams_frame, team, bg=hex_color))
            team_frames[team_index].grid(row=team_index, column=0, sticky='nsew', pady=(0, 10))


class WatcherFrame(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.master = master

        config_grids(self, rows=[0, 0], columns=[1])

        self.toggle_watcher_button = tk.Button(
            self, bg=FG[1], fg=BG[1], bd=0, text='Start watcher', command=self.toggle_watcher
        )
        self.toggle_watcher_button.grid(row=0, column=0, sticky='ew', pady=(0, 5))

        self.watcher_status = tk.Label(self, text='Watcher stopped', bg=BG[0], fg=FG[3])
        self.watcher_status.grid(row=1, column=0, sticky='ew')


    def toggle_watcher(self):
        if self.master.watcher.isAlive(): # STOP
            self.master.watcher_queue.put('quit')
            self.master.watcher.join()
            self.toggle_watcher_button.config(text='Start watcher')
            self.watcher_status.config(text='Watcher stopped', fg=FG[3])
        else: # START
            self.master.watcher = smash_watcher.Watcher(self.master.watcher_queue, self.master.queue)
            self.master.watcher.start()
            self.toggle_watcher_button.config(text='Stop watcher')
            self.watcher_status.config(fg=FG[6])
            self.master.game_frame.destroy()
            self.master.game_frame = GameFrame(self.master, bg=BG[1])
            self.master.game_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)


class Window(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.master = master
        self.watcher = None
        self.cont = True
        self.queue = Queue()
        self.watcher_queue = Queue()

        self.watcher = smash_watcher.Watcher(self.watcher_queue, self.queue)
        self.watcher.daemon = True

        self.game = None

        self.restart_flag = False

        self.pack(fill=tk.BOTH, expand=True)

        self.master.title(TITLE)

        config_grids(self, rows=[0, 1], columns=[1])

        self.game_frame = GameFrame(self, bg=BG[1])
        self.game_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)

        self.watcher_frame = WatcherFrame(self, bg=BG[0])
        self.watcher_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

        self.menubar = Menubar(self)
        self.master.config(menu=self.menubar)

        self.loop()


    def loop(self):
        if self.cont:
            self.check_queue()
            self.master.after(100, self.loop)


    def check_queue(self):
        try:
            item = self.queue.get(block=False)
            if item == 'update':
                self.game_frame.display_info()
            if 'status' in item:
                self.watcher_frame.watcher_status.config(text=item['status'])
        except Empty:
            pass


    def quit(self):
        self.cont = False
        self.master.destroy()


    def restart(self):
        self.quit()
        self.restart_flag = True


def run_gui():
    root = tk.Tk()
    root.geometry('540x550')
    # root.iconbitmap(os.path.join(BASE_DIR, 'icon.ico'))
    window = Window(root, bg=BG[0])

    root.mainloop()

    if window.watcher.isAlive():
        window.watcher_queue.put('quit')
        window.watcher.join()

    if window.restart_flag:
        os.system(__file__)


def headless():
    queue = Queue()
    watcher_queue = Queue()
    watcher = smash_watcher.Watcher(watcher_queue, queue)
    # watcher.daemon = True
    watcher.start()
    _input = ''
    while _input not in ['stop', 'exit', 'quit']:
        _input = input('>: ')
    key_capture.put('quit')
    key_capture.join()
    watcher_queue.put('quit')
    watcher.join()


if __name__ == '__main__':
    print(f'\n\n{"*" * 40} {TITLE} {"*" * 40}')
    print(f'<<<{datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")}>>>')
    # settings = ut.load_settings()
    if len(argv):
        if '-nogui' in argv:
            headless()
        else:
            run_gui()
